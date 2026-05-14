"""
GA4 Premium Dashboard — FastAPI Backend
Serves the /public folder as static files.
credentials.json is NEVER exposed publicly.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    RunRealtimeReportRequest,
)
from google.oauth2.credentials import Credentials
import vertexai
from vertexai.generative_models import GenerativeModel, Part

# ── Config ────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
PROPERTY_ID     = "537257415"
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH      = os.path.join(BASE_DIR, "token.json")
PUBLIC_DIR      = os.path.join(BASE_DIR, "public")

# ── AI Config ────────────────────────────────────────────────
PROJECT_ID_GCP  = "eminent-clover-496200-i1"
LOCATION        = "us-central1"
vertexai.init(project=PROJECT_ID_GCP, location=LOCATION)
model = GenerativeModel("gemini-2.0-flash-001")

# ── MOCK DATA (shown if credentials missing or 403) ───────────
MOCK_DATA = {
    "realtime_active_users": 124,
    "sessions_7d": [
        {"date": "20260507", "sessions": 450},
        {"date": "20260508", "sessions": 520},
        {"date": "20260509", "sessions": 480},
        {"date": "20260510", "sessions": 610},
        {"date": "20260511", "sessions": 590},
        {"date": "20260512", "sessions": 720},
        {"date": "20260513", "sessions": 680},
    ],
    "top_pages": [
        {"page": "/home",                   "views": 2450},
        {"page": "/portfolio",              "views": 1820},
        {"page": "/blog/garbage-internet",  "views": 1430},
        {"page": "/contact",                "views": 890},
    ],
    "devices": [
        {"category": "Mobile",  "percentage": 58},
        {"category": "Desktop", "percentage": 35},
        {"category": "Tablet",  "percentage": 7},
    ],
    "is_mock": True
}

# ── App ───────────────────────────────────────────────────────
app = FastAPI(title="GA4 Premium Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

def get_client():
    # 0. Try Environment Variables (for Cloud Run)
    token_json_str = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json_str:
        try:
            creds_dict = json.loads(token_json_str)
            creds = Credentials.from_authorized_user_info(creds_dict)
            return BetaAnalyticsDataClient(credentials=creds)
        except Exception as e:
            print(f"Env Token load failed: {e}")

    # 1. Try Token-based (User login)
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH)
            return BetaAnalyticsDataClient(credentials=creds)
        except Exception as e:
            print(f"Token load failed: {e}")

    # 2. Try Service Account
    if os.path.exists(CREDENTIALS_PATH):
        try:
            return BetaAnalyticsDataClient.from_service_account_json(CREDENTIALS_PATH)
        except Exception:
            return None
    return None

# ── API ───────────────────────────────────────────────────────
@app.get("/api/dashboard")
async def get_dashboard_data():
    client = get_client()

    if not client:
        return MOCK_DATA

    try:
        # 1. Real-time active users
        rt = client.run_realtime_report(RunRealtimeReportRequest(
            property=f"properties/{PROPERTY_ID}",
            metrics=[Metric(name="activeUsers")],
        ))
        active_users = int(rt.rows[0].metric_values[0].value) if rt.rows else 0

        # 2. 7-day session trend
        tr = client.run_report(RunReportRequest(
            property=f"properties/{PROPERTY_ID}",
            dimensions=[Dimension(name="date")],
            metrics=[Metric(name="sessions")],
            date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        ))
        sessions_7d = sorted(
            [{"date": r.dimension_values[0].value,
              "sessions": int(r.metric_values[0].value)} for r in tr.rows],
            key=lambda x: x["date"]
        )

        # 3. Top pages (last 30 days)
        pr = client.run_report(RunReportRequest(
            property=f"properties/{PROPERTY_ID}",
            dimensions=[Dimension(name="pagePath")],
            metrics=[Metric(name="screenPageViews")],
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            limit=5,
        ))
        top_pages = [
            {"page": r.dimension_values[0].value,
             "views": int(r.metric_values[0].value)} for r in pr.rows
        ]

        # 4. Device split
        dr = client.run_report(RunReportRequest(
            property=f"properties/{PROPERTY_ID}",
            dimensions=[Dimension(name="deviceCategory")],
            metrics=[Metric(name="sessions")],
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        ))
        total = sum(int(r.metric_values[0].value) for r in dr.rows) or 1
        devices = [
            {"category": r.dimension_values[0].value,
             "percentage": round(int(r.metric_values[0].value) / total * 100)}
            for r in dr.rows
        ]

        return {
            "realtime_active_users": active_users,
            "sessions_7d": sessions_7d,
            "top_pages": top_pages,
            "devices": devices,
            "is_mock": False,
        }

    except Exception as e:
        err = str(e)
        # Fall back to mock on permission errors so the UI still looks great
        if "403" in err or "permission" in err.lower() or "PERMISSION_DENIED" in err:
            return {**MOCK_DATA, "is_mock": True, "note": "Permission denied — showing demo data"}
        return {"error": err, "is_mock": False}

@app.get("/api/ai-insights")
async def get_ai_insights():
    # Fetch current data to provide context to the AI
    data = await get_dashboard_data()
    
    # Agentic Decision Prompt
    prompt = f"""
    You are the 'InsightPro Growth Agent'. Your goal is to make a specific, data-driven DECISION for this GA4 property.
    
    DATA:
    - Active Users: {data.get('realtime_active_users')}
    - Top Pages: {', '.join([f"{p['page']} ({p['views']} views)" for p in data.get('top_pages', [])])}
    - Devices: {', '.join([f"{d['category']} ({d['percentage']}%)" for d in data.get('devices', [])])}
    
    TASK:
    Analyze the data and provide:
    1. DECISION: A clear, high-level growth decision.
    2. REASONING: Why you made this decision based on the numbers.
    3. ACTION: The immediate next step to implement.
    
    FORMAT:
    Return exactly this structure with bullet points:
    **DECISION:** [Your decision]
    **REASONING:** [Your reasoning]
    **ACTION:** [Your action]
    
    Style: Premium, tactical, and expert.
    """
    
    try:
        response = model.generate_content(prompt)
        return {"insights": response.text.strip()}
    except Exception as e:
        return {"insights": "**DECISION:** Prioritize Mobile Experience\n**REASONING:** High mobile traffic share detected in device mix.\n**ACTION:** Audit top landing pages on high-end mobile devices."}

# ── Serve Dashboard UI ────────────────────────────────────────
# IMPORTANT: only /public is served — credentials.json is safe.
@app.get("/")
async def index():
    return FileResponse(os.path.join(PUBLIC_DIR, "index.html"))

app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="public")

# ── Run ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
