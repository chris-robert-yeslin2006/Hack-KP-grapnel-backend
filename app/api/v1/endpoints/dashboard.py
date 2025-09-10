# app/routers/dashboard.py
from fastapi import APIRouter, HTTPException
import plotly.graph_objects as go
import plotly.utils
from datetime import datetime, timedelta
from httpx import AsyncClient
 # import the FastAPI app for in-process calls

router = APIRouter(tags=["dashboard"])

# ---------- Overview ----------
@router.get("/overview")
async def get_dashboard_overview():
    from app.main import app 
    async with AsyncClient(app=app, base_url="https://hack-kp-grapnel-backend.onrender.com") as client:
        # Hash stats
        
        stats_resp = await client.get("/api/v1/hashes/stats")
        if stats_resp.status_code != 200:
            raise HTTPException(500, "Failed to fetch hash stats")
        stats = stats_resp.json()

        # Health
        health_resp = await client.get("/api/v1/health")
        health = health_resp.json() if health_resp.status_code == 200 else {}

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "stats": stats,
        "alerts": [],  # will fill later
        "system_status": health,
    }

# ---------- Hash Activity ----------
@router.get("/hash-activity")
async def get_hash_activity_chart():
    from app.main import app 
    end_time = datetime.utcnow()
    hours = [end_time - timedelta(hours=i) for i in range(24)][::-1]

    async with AsyncClient(app=app, base_url="http://test") as client:
        stats_resp = await client.get("/api/v1/hashes/stats")
        total_hashes = stats_resp.json().get("total_hashes", 0) if stats_resp.status_code == 200 else 0

    values = [max(0, total_hashes // 24) for _ in hours]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours,
        y=values,
        mode="lines+markers",
        name="Total Hashes",
        line=dict(color="#4ECDC4", width=3),
    ))

    fig.update_layout(
        title="📊 Hash Activity - Last 24 Hours",
        xaxis_title="Time",
        yaxis_title="Hash Count",
        template="plotly_dark",
        hovermode="x unified",
    )

    return {"chart_data": plotly.utils.PlotlyJSONEncoder().encode(fig)}

# ---------- Match Heatmap ----------
@router.get("/match-heatmap")
async def get_match_heatmap():
    systems = ["trace", "grapnel", "takedown"]

    values = [[0 if i == j else (i + j) * 5 for j in range(len(systems))] for i in range(len(systems))]
    labels = [[str(v) for v in row] for row in values]

    fig = go.Figure(data=go.Heatmap(
        z=values,
        x=systems,
        y=systems,
        colorscale="Reds",
        text=labels,
        texttemplate="%{text}",
        textfont={"size": 16},
    ))

    fig.update_layout(title="🔥 Cross-System Hash Match Heatmap", template="plotly_dark")

    return {"chart_data": plotly.utils.PlotlyJSONEncoder().encode(fig)}

# ---------- Alerts Timeline ----------
@router.get("/alerts-timeline")
async def get_alerts_timeline():
    alerts = [
        {"timestamp": datetime.utcnow().isoformat(), "severity": "critical"},
        {"timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(), "severity": "high"},
        {"timestamp": (datetime.utcnow() - timedelta(hours=5)).isoformat(), "severity": "medium"},
    ]

    fig = go.Figure()
    for sev, lvl, color, size, sym in [
        ("critical", 4, "red", 15, "triangle-up"),
        ("high", 3, "orange", 12, "circle"),
        ("medium", 2, "yellow", 10, "circle"),
    ]:
        sev_alerts = [a for a in alerts if a["severity"] == sev]
        if sev_alerts:
            fig.add_trace(go.Scatter(
                x=[a["timestamp"] for a in sev_alerts],
                y=[lvl] * len(sev_alerts),
                mode="markers",
                name=sev.title(),
                marker=dict(color=color, size=size, symbol=sym),
            ))

    fig.update_layout(
        title="⚡ Alert Timeline - Real-time Monitoring",
        xaxis_title="Time",
        yaxis_title="Severity Level",
        yaxis=dict(
            tickmode="array",
            tickvals=[1, 2, 3, 4],
            ticktext=["Low", "Medium", "High", "Critical"],
        ),
        template="plotly_dark",
    )

    return {"chart_data": plotly.utils.PlotlyJSONEncoder().encode(fig)}
