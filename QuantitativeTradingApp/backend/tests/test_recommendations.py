"""推荐接口测试：股票校验 / 持仓录入 / 偏好 / 全局与个性化推荐。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models import Recommendation, StrategyRun, User, UserPersonalAdvice


def test_stock_search(client, stock_factory):
    stock_factory("600519.SH", "贵州茅台")
    resp = client.get("/api/stocks/search", params={"q": "茅台"})
    assert resp.status_code == 200
    codes = [s["code"] for s in resp.json()]
    assert "600519.SH" in codes


def test_position_requires_existing_stock(client, auth_headers):
    headers = auth_headers("posuser")
    resp = client.post(
        "/api/positions",
        json={"stock_code": "999999.SS", "shares": 100, "cost_price": 10},
        headers=headers,
    )
    assert resp.status_code == 404


def test_position_upsert_and_preferences(client, auth_headers, stock_factory):
    stock_factory("600036.SH", "招商银行")
    headers = auth_headers("prefuser")

    resp = client.post(
        "/api/positions",
        json={"stock_code": "600036.SH", "shares": 100, "cost_price": 30},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["shares"] == 100

    resp = client.post(
        "/api/positions",
        json={"stock_code": "600036.SH", "shares": 200, "cost_price": 31},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["shares"] == 200

    resp = client.get("/api/preferences", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["risk_level"] == "moderate"

    resp = client.put(
        "/api/preferences",
        json={"risk_level": "aggressive", "total_capital": 1000000},
        headers=headers,
    )
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["total_capital"])) == Decimal("1000000")


def test_recommendations_require_auth(client):
    assert client.get("/api/recommendations/global").status_code == 401
    assert client.get("/api/recommendations/personal").status_code == 401


def test_global_recommendations_pagination_and_filter(
    client, auth_headers, db_session, stock_factory
):
    stock_factory("600000.SH", "浦发银行")
    stock_factory("600036.SH", "招商银行")
    run = StrategyRun(strategy="turtle", run_date=date(2026, 7, 31), status="success")
    db_session.add(run)
    db_session.flush()
    db_session.add(
        Recommendation(
            run_id=run.id,
            run_date=date(2026, 7, 31),
            strategy="turtle",
            stock_code="600000.SH",
            signal="BUY",
            score=80,
            close=11.2,
            reason="突破",
        )
    )
    db_session.add(
        Recommendation(
            run_id=run.id,
            run_date=date(2026, 7, 31),
            strategy="bollinger_mean_reversion",
            stock_code="600036.SH",
            signal="HOLD",
            score=50,
            close=30.0,
        )
    )
    db_session.commit()

    headers = auth_headers("reccuser")
    resp = client.get("/api/recommendations/global", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["stock_name"] in ("浦发银行", "招商银行")

    filtered = client.get(
        "/api/recommendations/global",
        params={"strategy": "turtle"},
        headers=headers,
    )
    assert filtered.json()["total"] == 1


def test_personal_recommendations_ordering(
    client, auth_headers, db_session, stock_factory
):
    stock_factory("600000.SH", "浦发银行")
    stock_factory("600036.SH", "招商银行")
    headers = auth_headers("persuser")

    user = db_session.scalar(select(User).where(User.username == "persuser"))
    db_session.add(
        UserPersonalAdvice(
            user_id=user.id,
            stock_code="600000.SH",
            advice_date=date(2026, 7, 31),
            action="BUY",
            suggested_shares=100,
            reason="建仓",
            strategy_signals=[{"strategy": "turtle", "signal": "BUY"}],
        )
    )
    db_session.add(
        UserPersonalAdvice(
            user_id=user.id,
            stock_code="600036.SH",
            advice_date=date(2026, 7, 31),
            action="SELL",
            suggested_shares=0,
            reason="止损",
            strategy_signals=[{"strategy": "turtle", "signal": "AVOID"}],
        )
    )
    db_session.commit()

    resp = client.get("/api/recommendations/personal", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert [i["action"] for i in body["items"]] == ["BUY", "SELL"]
    assert body["items"][0]["strategy_signals"][0]["strategy"] == "turtle"
