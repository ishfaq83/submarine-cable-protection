import os
import json
import time
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from services.ais_service import AISTrackerService
from services.dark_vessel_engine import DarkVesselEngine
from services.alert_service import AlertService
from services.auth_service import AuthService

app = FastAPI(
    title="Submarine Cable Protection & AIS Maritime Intelligence API",
    description="Intelligent Maritime Surveillance & Cable Protection System API",
    version="1.0.0"
)

# Enable CORS for frontend web GIS dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base data path
CABLES_FILE = os.path.join(os.path.dirname(__file__), "data", "cables.json")

# Initialize Services
ais_service = AISTrackerService(CABLES_FILE)
dark_vessel_engine = DarkVesselEngine()
alert_service = AlertService()
auth_service = AuthService()

# Pydantic Schemas
class SimulationToggleRequest(BaseModel):
    running: bool

class LoginRequest(BaseModel):
    email: str
    password: str

@app.get("/")
def read_root():
    return {
        "system": "Submarine Cable Protection & AIS Maritime Intelligence",
        "status": "OPERATIONAL",
        "description": "Submarine Cable Protection & AIS Maritime Surveillance System",
        "modules": [
            "Module 1: GIS Map Dashboard",
            "Module 2: AIS Vessel Tracking",
            "Module 3: Submarine Cable GeoJSON Database",
            "Module 4: Multi-Tier Spatial Geo-Fencing Engine",
            "Module 5: AI Risk Engine (Score 0-100)",
            "Module 6: Dark Vessel Satellite SAR Detection",
            "Module 7: Alert Notification System",
            "Module 8: Security & Audit Logging"
        ],
        "version": "1.0.0"
    }

@app.get("/api/cables")
def get_cables():
    """
    Module 3: Returns GeoJSON FeatureCollection of Submarine Cable Routes & Protection Buffer Info.
    """
    with open(CABLES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

@app.get("/api/vessels")
def get_vessels():
    """
    Module 2 & 5: Returns live AIS vessel positions, spatial cable proximity, and AI risk scores.
    """
    vessels = ais_service.get_all_vessels()
    # Evaluate alerts dynamically
    alert_service.evaluate_vessel_alerts(vessels)
    return vessels

@app.get("/api/vessel/{mmsi}")
def get_vessel(mmsi: str):
    vessel = ais_service.get_vessel_by_mmsi(mmsi)
    if not vessel:
        raise HTTPException(status_code=404, detail="Vessel MMSI not found")
    history = ais_service.get_vessel_history(mmsi)
    return {
        "vessel": vessel,
        "track_history": history
    }

@app.get("/api/track/history")
def get_all_track_histories():
    """
    Returns full position trail histories for all tracked vessels.
    """
    vessels = ais_service.get_all_vessels()
    histories = {}
    for v in vessels:
        mmsi = v["mmsi"]
        histories[mmsi] = ais_service.get_vessel_history(mmsi)
    return histories

@app.get("/api/alerts")
def get_alerts():
    """
    Module 4 & 7: Returns current geofence and risk alerts.
    """
    vessels = ais_service.get_all_vessels()
    alerts = alert_service.evaluate_vessel_alerts(vessels)
    return alerts

@app.post("/api/alerts/acknowledge/{alert_id}")
def acknowledge_alert(alert_id: str):
    res = alert_service.acknowledge_alert(alert_id)
    if not res:
        raise HTTPException(status_code=404, detail="Alert ID not found")
    auth_service.log_action("Operator User", "Operator", "ALERT_ACKNOWLEDGE", f"Acknowledged alert {alert_id}")
    return res

@app.get("/api/dark-vessels")
def get_dark_vessels():
    """
    Module 6: Returns detected Dark Vessels from Satellite SAR radar scans.
    """
    return dark_vessel_engine.get_dark_vessels()

@app.post("/api/dark-vessels/scan")
def trigger_sar_scan():
    """
    Triggers a fresh Sentinel-1 satellite SAR orbital sweep.
    """
    active_vessels = ais_service.get_all_vessels()
    res = dark_vessel_engine.run_satellite_sar_sweep(active_vessels)
    auth_service.log_action("Dr. Alex Rivera", "GIS Analyst", "SENTINEL_SAR_SCAN", "Completed Sentinel-1 satellite orbital scan")
    return res

@app.post("/api/simulation/inject-suspicious")
def inject_suspicious():
    v = ais_service.inject_suspicious_vessel()
    auth_service.log_action("Operator", "Operator", "SIMULATION_INJECT", f"Injected high-risk suspicious vessel MMSI {v['mmsi']}")
    return {"message": "Suspicious vessel injected into 500m MAREA critical zone", "vessel": v}

@app.post("/api/simulation/toggle")
def toggle_simulation(req: SimulationToggleRequest):
    ais_service.simulation_running = req.running
    return {"simulation_running": ais_service.simulation_running}

@app.get("/api/analytics")
def get_analytics():
    vessels = ais_service.get_all_vessels()
    alerts = alert_service.evaluate_vessel_alerts(vessels)
    dark_vessels = dark_vessel_engine.get_dark_vessels()
    
    high_risk_count = sum(1 for v in vessels if v.get("risk_assessment", {}).get("score", 0) >= 61)
    critical_alerts = sum(1 for a in alerts if a.get("risk_level") == "CRITICAL" and not a.get("acknowledged"))

    return {
        "cables_monitored": 5,
        "total_active_vessels": len(vessels),
        "high_risk_vessels": high_risk_count,
        "unacknowledged_critical_alerts": critical_alerts,
        "dark_vessels_detected": len(dark_vessels),
        "system_status": "OPTIMAL",
        "last_satellite_pass": dark_vessel_engine.last_scan_timestamp
    }

@app.post("/api/auth/login")
def login(req: LoginRequest):
    if req.email in auth_service.users:
        user = auth_service.users[req.email]
        auth_service.log_action(user["name"], user["role"], "USER_LOGIN", f"User {user['email']} logged in.")
        return user
    return auth_service.users["admin@oceanguard.ai"]

@app.get("/api/audit-logs")
def get_audit_logs():
    return auth_service.get_audit_logs()
