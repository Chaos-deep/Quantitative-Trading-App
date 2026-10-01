"""模块一·数据工厂：A 股数据获取（akshare 主 + efinance 备）。

适配器模式，market 参数当前支持 SH/SZ/BJ（预留 HK/US）。
降级策略：按股票粒度重试（最多 3 次）→ 切备用源 → 记录失败清单，不阻断整体流程。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailyBar, Stock
from app.utils.db import upsert_rows
from app.utils.dates import today_shanghai
from app.utils.logging import get_logger

logger = get_logger("market_data")

HISTORY_DAYS = 400  # 覆盖 MA(250) + 缓冲
MAX_RETRY = 3
FETCH_WORKERS = 6  # 日线并发抓取线程数（网络并行，DB 写入仍单线程）


def _normalize_code(raw: str) -> str:
    """6 位代码 → 规范 code（带交易所后缀）。"""
    raw = raw.strip().upper()
    if "." in raw:
        return raw
    if raw.startswith(("60", "68", "5", "9")):
        return f"{raw}.SH"
    if raw.startswith(("00", "30", "20", "12")):
        return f"{raw}.SZ"
    if raw.startswith(("43", "83", "87", "92", "4", "8")):
        return f"{raw}.BJ"
    return f"{raw}.SH"


def _market_of(code: str) -> str:
    return code.rsplit(".", 1)[-1] if "." in code else ""


@dataclass
class StockInfo:
    code: str
    name: str
    market: str


@dataclass
class FetchStats:
    total: int = 0
    ok: int = 0
    failed: list[str] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)


class BaseProvider(ABC):
    """行情数据源抽象接口。"""

    name: str = ""

    @abstractmethod
    def get_stock_list(self) -> list[StockInfo]: ...

    @abstractmethod
    def get_daily_bars(self, symbol: str, start: date, end: date) -> pd.DataFrame: ...

    def get_trade_dates(self) -> Optional[set[date]]:
        """交易日历；无法获取返回 None（调用方回退星期判断）。"""
        return None


def _normalize_bars(df: pd.DataFrame) -> pd.DataFrame:
    """统一列名：date/open/high/low/close/volume/amount（volume 单位保持数据源：手）。"""
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "amount"])
    rename = {
        "日期": "date", "开盘": "open", "收盘": "close",
        "最高": "high", "最低": "low", "成交量": "volume", "成交额": "amount",
    }
    df = df.rename(columns=rename)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    else:
        df["amount"] = 0.0
    keep = ["date", "open", "high", "low", "close", "volume", "amount"]
    return df[[c for c in keep if c in df.columns]].dropna(subset=["date", "close"])


class AkshareProvider(BaseProvider):
    """主数据源。数据获取失败抛异常，由 MarketDataService 降级。"""

    name = "akshare"

    def _ak(self):
        import akshare as ak  # 懒加载：避免重依赖拖慢启动

        return ak

    def get_stock_list(self) -> list[StockInfo]:
        ak = self._ak()
        df = ak.stock_info_a_code_name()
        items: list[StockInfo] = []
        for _, row in df.iterrows():
            code = _normalize_code(str(row["code"]))
            items.append(StockInfo(code=code, name=str(row["name"]).strip(), market=_market_of(code)))
        return items

    def get_daily_bars(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        ak = self._ak()
        code, _, market = symbol.partition(".")
        if not market:
            market = _market_of(_normalize_code(code))
        tx_symbol = f"{market.lower()}{code}"
        # 使用腾讯行情接口（stock_zh_a_hist_tx）：部分网络环境下东方财富接口不可达
        df = ak.stock_zh_a_hist_tx(
            symbol=tx_symbol,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
        )
        return _normalize_bars(df)

    def get_trade_dates(self) -> Optional[set[date]]:
        try:
            ak = self._ak()
            df = ak.tool_trade_date_hist_sina()
            return set(pd.to_datetime(df["trade_date"]).dt.date)
        except Exception:
            logger.warning("akshare 交易日历获取失败，回退星期判断", exc_info=True)
            return None


class EfinanceProvider(BaseProvider):
    """备用数据源（akshare 异常时降级）。"""

    name = "efinance"

    def _ef(self):
        import efinance as ef  # 懒加载

        return ef

    def get_stock_list(self) -> list[StockInfo]:
        ef = self._ef()
        df = ef.stock.get_realtime_quotes()
        items: list[StockInfo] = []
        for _, row in df.iterrows():
            code = _normalize_code(str(row["股票代码"]))
            items.append(StockInfo(code=code, name=str(row["股票名称"]).strip(), market=_market_of(code)))
        return items

    def get_daily_bars(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        ef = self._ef()
        df = ef.stock.get_quote_history(symbol, beg=start.strftime("%Y%m%d"), end=end.strftime("%Y%m%d"))
        return _normalize_bars(df)


class TradingCalendar:
    """交易日判断：优先 akshare 日历，失败回退工作日判断。"""

    def __init__(self, provider: BaseProvider | None = None, fallback_weekdays: bool = True):
        self.provider = provider
        self._dates: set[date] | None = None
        self.fallback_weekdays = fallback_weekdays

    def is_trading_day(self, day: date) -> bool:
        if self._dates is None and self.provider is not None:
            self._dates = self.provider.get_trade_dates()
        if self._dates is not None:
            return day in self._dates
        return self.fallback_weekdays and day.weekday() < 5


class MarketDataService:
    """模块一编排：列表同步 + 全市场日线拉取（主源→备用源降级）。"""

    def __init__(
        self,
        session: Session,
        primary: BaseProvider | None = None,
        backup: BaseProvider | None = None,
        calendar: TradingCalendar | None = None,
        history_days: int = HISTORY_DAYS,
        max_retry: int = MAX_RETRY,
    ):
        self.session = session
        self.primary = primary or AkshareProvider()
        self.backup = backup or EfinanceProvider()
        self.calendar = calendar or TradingCalendar(provider=self.primary)
        self.history_days = history_days
        self.max_retry = max_retry

    # ---- 股票列表 ----

    def sync_stock_list(self) -> FetchStats:
        stats = FetchStats()
        items: list[StockInfo] | None = None
        for attempt in range(self.max_retry):
            try:
                items = self.primary.get_stock_list()
                break
            except Exception:
                logger.warning(
                    "股票列表获取失败[%s] attempt=%s", self.primary.name, attempt, exc_info=True
                )
        if items is None:
            # 降级：沿用数据库已有股票列表，不阻断整体流水线
            existing = self.session.scalars(
                select(Stock.code).where(Stock.status == "active")
            ).all()
            if existing:
                logger.warning("股票列表获取失败，沿用现有 %s 只股票继续", len(existing))
                stats.total = len(existing)
                return stats
            raise RuntimeError("股票列表获取失败：主备数据源均不可用")
        stats.total = len(items)

        upsert_rows(
            self.session,
            Stock,
            [{"code": it.code, "name": it.name, "market": it.market, "status": "active"} for it in items],
            index_elements=["code"],
            update_columns=["name", "market", "status"],
        )

        # 退市检测：之前 active 但不在当前列表 → delisted
        current = {it.code for it in items}
        active = self.session.scalars(select(Stock.code).where(Stock.status == "active")).all()
        for code in active:
            if code not in current:
                st = self.session.get(Stock, code)
                if st is not None:
                    st.status = "delisted"
        self.session.commit()
        return stats

    # ---- 日线拉取 ----

    def _fetch_with_degrade(self, code: str, symbol: str, start: date, end: date, stats: FetchStats) -> pd.DataFrame:
        """按股票粒度重试（最多 3 次），akshare 失败切 efinance 降级。"""
        for attempt in range(self.max_retry):
            provider = self.primary if attempt % 2 == 0 else self.backup
            try:
                df = provider.get_daily_bars(symbol, start, end)
                if df is None or df.empty:
                    raise ValueError(f"{provider.name} 返回空数据")
                if provider.name != self.primary.name:
                    stats.degraded.append(code)
                return df
            except Exception:
                logger.warning("日线获取失败 %s [%s] attempt=%s", code, provider.name, attempt, exc_info=True)
        raise RuntimeError(f"{code} 日线获取失败（重试 {self.max_retry} 次）")

    def fetch_all_daily_bars(self, target: date | None = None) -> FetchStats:
        """拉取全市场日线并批量写入 daily_bars（幂等）。

        网络抓取并发执行（ThreadPoolExecutor），数据库写入保持单线程
        （SQLAlchemy Session 非线程安全），每批 5000 行提交一次。
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        target = target or today_shanghai()
        start = target - timedelta(days=self.history_days)
        codes = self.session.scalars(select(Stock.code).where(Stock.status == "active")).all()
        stats = FetchStats(total=len(codes))

        def fetch_one(code: str):
            local = FetchStats()
            try:
                df = self._fetch_with_degrade(code, code.split(".")[0], start, target, local)
                return code, df, local, None
            except Exception as exc:  # noqa: BLE001
                return code, None, local, exc

        buffer: list[dict] = []
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
            futures = [pool.submit(fetch_one, code) for code in codes]
            for future in as_completed(futures):
                code, df, local, err = future.result()
                if err is not None or df is None or df.empty:
                    stats.failed.append(code)
                else:
                    stats.degraded.extend(local.degraded)
                    stats.ok += 1
                    buffer.extend(
                        {
                            "stock_code": code,
                            "date": row.date,
                            "open": float(row.open),
                            "high": float(row.high),
                            "low": float(row.low),
                            "close": float(row.close),
                            "volume": int(row.volume),
                            "amount": float(row.amount) if pd.notna(row.amount) else None,
                        }
                        for row in df.itertuples()
                        if row.date <= target
                    )
                if len(buffer) >= 5000:
                    self._write_bars(buffer)
                    buffer.clear()
        if buffer:
            self._write_bars(buffer)
        self.session.commit()
        return stats

    def _write_bars(self, rows: list[dict]) -> None:
        from app.utils.db import insert_rows_ignore_conflict

        insert_rows_ignore_conflict(
            self.session,
            DailyBar,
            rows,
            index_elements=["stock_code", "date"],
        )
        self.session.commit()
