"""
GA4 Premium Dashboard — FastAPI Backend
Serves the /public folder as static files.
credentials.json is NEVER exposed publicly.
"""
import os
import json
import datetime
from fastapi import FastAPI, Header, HTTPException, Depends
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
from google.oauth2 import service_account
import googleapiclient.discovery
import vertexai
from vertexai.generative_models import GenerativeModel, Part

# ── Config ────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
PROPERTY_ID     = "537257415"
GSC_PROPERTY    = "sc-domain:youssefmccarthy.com" # Default assumption
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH      = os.path.join(BASE_DIR, "token.json")
PUBLIC_DIR      = os.path.join(BASE_DIR, "public")

# ── AI Config ────────────────────────────────────────────────
PROJECT_ID_GCP  = "eminent-clover-496200-i1"
LOCATION        = "us-central1"
vertexai.init(project=PROJECT_ID_GCP, location=LOCATION)
model = GenerativeModel("gemini-3.1-pro")

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
    "sources": [
        {"source": "google", "sessions": 1250},
        {"source": "direct", "sessions": 850},
        {"source": "linkedin.com", "sessions": 420},
        {"source": "newsletter", "sessions": 210},
    ],
    "audience": [
        {"country": "United States", "sessions": 520, "engagement_rate": 65.2, "bounce_rate": 34.8},
        {"country": "United Kingdom", "sessions": 210, "engagement_rate": 58.1, "bounce_rate": 41.9},
        {"country": "Canada", "sessions": 150, "engagement_rate": 61.5, "bounce_rate": 38.5},
    ],
    "gsc_data": [
        {"query": "youssef mccarthy", "clicks": 145, "impressions": 850, "ctr": 17.06, "position": 1.2},
        {"query": "data analytics portfolio", "clicks": 85, "impressions": 1200, "ctr": 7.08, "position": 4.5},
        {"query": "ga4 dashboard python", "clicks": 42, "impressions": 950, "ctr": 4.42, "position": 8.1},
    ],
    "is_mock": True
}

# ── App ───────────────────────────────────────────────────────
app = FastAPI(title="GA4 Expert Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_clients():
    creds = None
    
    # 0. Try Environment Variables (for Cloud Run)
    token_json_str = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json_str:
        try:
            creds_dict = json.loads(token_json_str)
            creds = Credentials.from_authorized_user_info(creds_dict)
        except Exception as e:
            print(f"Env Token load failed: {e}")

    # 1. Try Token-based (User login)
    elif os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH)
        except Exception as e:
            print(f"Token load failed: {e}")

    # 2. Try Service Account
    elif os.path.exists(CREDENTIALS_PATH):
        try:
            creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
        except Exception as e:
            print(f"Service Account load failed: {e}")

    if not creds:
        return None, None

    try:
        ga_client = BetaAnalyticsDataClient(credentials=creds)
        gsc_client = googleapiclient.discovery.build('webmasters', 'v3', credentials=creds, cache_discovery=False)
        return ga_client, gsc_client
    except Exception as e:
        print(f"Client build failed: {e}")
        return None, None

# ── Security ──────────────────────────────────────────────────
async def verify_api_key(x_api_key: str = Header(None)):
    expected_password = os.environ.get("DASHBOARD_PASSWORD", "Praetorian2026")
    if not x_api_key or x_api_key != expected_password:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_api_key

# ── API ───────────────────────────────────────────────────────
@app.get("/api/dashboard")
async def get_dashboard_data(api_key: str = Depends(verify_api_key)):
    return await fetch_dashboard_data()

async def fetch_dashboard_data():
    ga_client, gsc_client = get_clients()

    if not ga_client:
        return MOCK_DATA

    try:
        # 1. Real-time active users
        rt = ga_client.run_realtime_report(RunRealtimeReportRequest(
            property=f"properties/{PROPERTY_ID}",
            metrics=[Metric(name="activeUsers")],
        ))
        active_users = int(rt.rows[0].metric_values[0].value) if rt.rows else 0

        # 2. 7-day session trend
        tr = ga_client.run_report(RunReportRequest(
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
        pr = ga_client.run_report(RunReportRequest(
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
        dr = ga_client.run_report(RunReportRequest(
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

        # 5. Top Sources
        sr = ga_client.run_report(RunReportRequest(
            property=f"properties/{PROPERTY_ID}",
            dimensions=[Dimension(name="sessionSource")],
            metrics=[Metric(name="sessions")],
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            limit=5,
        ))
        sources = [
            {"source": r.dimension_values[0].value,
             "sessions": int(r.metric_values[0].value)} for r in sr.rows
        ]

        # 6. Audience & Engagement (New)
        er = ga_client.run_report(RunReportRequest(
            property=f"properties/{PROPERTY_ID}",
            dimensions=[Dimension(name="country")],
            metrics=[Metric(name="sessions"), Metric(name="engagementRate"), Metric(name="bounceRate")],
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            limit=5,
        ))
        audience = [
            {"country": r.dimension_values[0].value,
             "sessions": int(r.metric_values[0].value),
             "engagement_rate": round(float(r.metric_values[1].value) * 100, 1),
             "bounce_rate": round(float(r.metric_values[2].value) * 100, 1)}
            for r in er.rows
        ]

        # 7. Google Search Console
        gsc_data = []
        if gsc_client:
            try:
                today = datetime.date.today().strftime("%Y-%m-%d")
                ago30 = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
                request = {
                    "startDate": ago30,
                    "endDate": today,
                    "dimensions": ["query"],
                    "rowLimit": 5
                }
                response = gsc_client.searchanalytics().query(siteUrl=GSC_PROPERTY, body=request).execute()
                if 'rows' in response:
                    for row in response['rows']:
                        gsc_data.append({
                            "query": row["keys"][0],
                            "clicks": row["clicks"],
                            "impressions": row["impressions"],
                            "ctr": round(row["ctr"] * 100, 2),
                            "position": round(row["position"], 1)
                        })
            except Exception as e:
                print(f"GSC query failed: {e}")

        return {
            "realtime_active_users": active_users,
            "sessions_7d": sessions_7d,
            "top_pages": top_pages,
            "devices": devices,
            "sources": sources,
            "audience": audience,
            "gsc_data": gsc_data,
            "is_mock": False,
        }

    except Exception as e:
        err = str(e)
        if "403" in err or "permission" in err.lower() or "PERMISSION_DENIED" in err:
            return {**MOCK_DATA, "is_mock": True, "note": "Permission denied — showing demo data"}
        return {"error": err, "is_mock": False}

@app.get("/api/ai-insights")
async def get_ai_insights(api_key: str = Depends(verify_api_key)):
    data = await fetch_dashboard_data()
    
    prompt = f"""
    You are the 'InsightPro Growth Agent', an expert Google Analytics 4 and SEO Specialist. Your goal is to make a specific, data-driven DECISION for this property.
    
    DATA (Last 30 Days):
    - Active Users: {data.get('realtime_active_users')}
    - Top Pages: {', '.join([f"{p['page']} ({p['views']} views)" for p in data.get('top_pages', [])])}
    - Top Sources: {', '.join([f"{s['source']} ({s['sessions']} sessions)" for s in data.get('sources', [])])}
    - Geo/Engagement: {', '.join([f"{a['country']} ({a['engagement_rate']}% engaged)" for a in data.get('audience', [])])}
    - Top SEO Queries (GSC): {', '.join([f"'{g['query']}' (Pos: {g['position']}, CTR: {g['ctr']}%)" for g in data.get('gsc_data', [])])}
    
    TASK:
    Analyze the cross-channel data (Analytics + Search Console) and provide:
    1. DECISION: A clear, high-level SEO or conversion optimization decision.
    2. REASONING: Why you made this decision, connecting the GA4 engagement metrics with GSC search data.
    3. ACTION: The immediate technical or content next step.
    
    FORMAT:
    Return exactly this structure with bullet points:
    **DECISION:** [Your decision]
    **REASONING:** [Your reasoning]
    **ACTION:** [Your action]
    
    Style: Premium, tactical, and expert. Speak like a senior data scientist.
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean markdown
        clean_text = response.text.replace('**DECISION:**', '<strong>DECISION:</strong><br>')
        clean_text = clean_text.replace('**REASONING:**', '<br><br><strong>REASONING:</strong><br>')
        clean_text = clean_text.replace('**ACTION:**', '<br><br><strong>ACTION:</strong><br>')
        html_insights = f"<p>{clean_text}</p>"
        return {"insights": html_insights}
    except Exception as e:
        return {"error": str(e)}

# Serve frontend
app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="public")
