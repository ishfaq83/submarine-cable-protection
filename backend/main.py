import os
import sys
import json
import time

# Ensure backend directory is on sys.path for internal service and provider imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from services.ais_service import AISTrackerService
from services.dark_vessel_engine import DarkVesselEngine
from services.alert_service import AlertService
from services.auth_service import AuthService
from services.risk_scoring_service import RiskScoringService

app = FastAPI(
    title="OceanGuard AI — Submarine Cable Protection & Maritime Intelligence API",
    description=(
        "Real-world maritime surveillance system combining AIS telemetry, "
        "Copernicus Sentinel-1 SAR primary radar detection, Sentinel-2 secondary optical confirmation, "
        "and an explainable cable-threat risk scoring engine."
    ),
    version="3.0.0"
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
risk_service = RiskScoringService()

# Pydantic Schemas
class SimulationToggleRequest(BaseModel):
    running: bool

class LoginRequest(BaseModel):
    email: str
    password: str

class RiskQueryRequest(BaseModel):
    mmsi: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    speed: Optional[float] = 0.0
    course: Optional[float] = 0.0
    vessel_type: Optional[str] = "Merchant"
    loitering_minutes: Optional[float] = 0.0

# ============================================================
# ROOT / HEALTH
# ============================================================

@app.get("/")
def read_root():
    return {
        "system": "OceanGuard AI — Submarine Cable Protection & Maritime Intelligence",
        "status": "OPERATIONAL",
        "version": "3.0.0",
        "phases_implemented": [
            "Phase 1: Real AIS Telemetry (Digitraffic / AISStream)",
            "Phase 2: Copernicus Sentinel-1 C-Band SAR Vessel Detection",
            "Phase 2.5: CA-CFAR SAR Image Pixel Processing Algorithm",
            "Phase 3: Sentinel-2 Optical Confirmation + Explainable Risk Engine"
        ],
        "modules": [
            "Module 1: GIS Map Dashboard",
            "Module 2: AIS Vessel Tracking (Real-World)",
            "Module 3: Submarine Cable GeoJSON Database",
            "Module 4: Multi-Tier Spatial Geo-Fencing Engine",
            "Module 5: Explainable Risk Engine (Score 0-100)",
            "Module 6: Dark Vessel Satellite SAR Detection (Sentinel-1)",
            "Module 7: Sentinel-2 Optical Secondary Confirmation",
            "Module 8: Alert Notification System",
            "Module 9: Security & Audit Logging"
        ]
    }

# ============================================================
# EXISTING ENDPOINTS (Preserved for frontend compatibility)
# ============================================================

@app.get("/api/cables")
def get_cables():
    """Module 3: Returns GeoJSON FeatureCollection of Submarine Cable Routes."""
    with open(CABLES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

@app.get("/api/vessels")
def get_vessels():
    """
    Module 2 & 5: Returns live AIS vessel positions, spatial cable proximity, and risk scores.
    """
    vessels = ais_service.get_all_vessels()
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
    """Returns full position trail histories for all tracked vessels."""
    vessels = ais_service.get_all_vessels()
    histories = {}
    for v in vessels:
        mmsi = v["mmsi"]
        histories[mmsi] = ais_service.get_vessel_history(mmsi)
    return histories

@app.get("/api/alerts")
def get_alerts():
    """
    Module 4 & 7: Returns current geofence and risk alerts (AIS + Satellite SAR + Optical).
    """
    vessels = ais_service.get_all_vessels()
    alert_service.evaluate_vessel_alerts(vessels)
    sat_detections = dark_vessel_engine.get_all_satellite_detections()
    alert_service.evaluate_satellite_alerts(sat_detections)
    return alert_service.alerts

@app.post("/api/alerts/acknowledge/{alert_id}")
def acknowledge_alert(alert_id: str):
    res = alert_service.acknowledge_alert(alert_id)
    if not res:
        raise HTTPException(status_code=404, detail="Alert ID not found")
    auth_service.log_action("Operator User", "Operator", "ALERT_ACKNOWLEDGE", f"Acknowledged alert {alert_id}")
    return res

@app.get("/api/dark-vessels")
def get_dark_vessels():
    """Module 6: Returns detected POTENTIAL DARK VESSELS from Sentinel-1 SAR scans."""
    return dark_vessel_engine.get_dark_vessels()

@app.post("/api/dark-vessels/scan")
def trigger_sar_scan():
    """
    Triggers a fresh Sentinel-1 SAR orbital sweep with Sentinel-2 secondary confirmation.
    Correlates with active AIS vessels. Evaluates satellite threat alerts.
    """
    active_vessels = ais_service.get_all_vessels()
    cable_features = ais_service.cables_data
    res = dark_vessel_engine.run_satellite_sar_sweep(active_vessels, cable_features=cable_features)
    alert_service.evaluate_satellite_alerts(dark_vessel_engine.get_all_satellite_detections())
    auth_service.log_action(
        "Dr. Alex Rivera", "GIS Analyst", "SENTINEL_SAR_SCAN",
        "Completed Sentinel-1/Sentinel-2 dual satellite orbital scan"
    )
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

    high_risk_count = sum(1 for v in vessels if v.get("risk_assessment", {}).get("risk_score", v.get("risk_assessment", {}).get("score", 0)) >= 61)
    critical_alerts = sum(1 for a in alerts if a.get("risk_level") == "CRITICAL" and not a.get("acknowledged"))

    return {
        "cables_monitored": 5,
        "total_active_vessels": len(vessels),
        "high_risk_vessels": high_risk_count,
        "unacknowledged_critical_alerts": critical_alerts,
        "dark_vessels_detected": len(dark_vessels),
        "system_status": "OPTIMAL",
        "last_satellite_pass": dark_vessel_engine.last_scan_timestamp,
        "satellite_providers": {
            "primary": "Copernicus Sentinel-1 C-Band SAR",
            "secondary": "Copernicus Sentinel-2 MSI Optical"
        }
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

@app.get("/api/providers/status")
def get_provider_status():
    """Returns health status, configuration, and coverage of all active data providers."""
    s1_health = dark_vessel_engine.sentinel1_provider.health_check()
    s2_health = dark_vessel_engine.sentinel2_provider.health_check()
    return {
        "ais_providers": ais_service.get_provider_status(),
        "satellite_providers": {
            "sentinel1_sar": s1_health,
            "sentinel2_optical": s2_health
        },
        "simulator_fallback_enabled": ais_service.use_simulator_fallback,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

# ============================================================
# NEW PHASE 3 ENDPOINTS
# ============================================================

@app.get("/api/risk")
def get_vessel_risk_scores():
    """
    Phase 3 — Explainable Risk Engine:
    Returns detailed cable-threat risk assessments for all active vessels,
    including contributing factors breakdown, data quality, and satellite evidence.
    """
    vessels = ais_service.get_all_vessels()
    cable_features = ais_service.cables_data
    risk_results = []

    for v in vessels:
        mmsi = v.get("mmsi", "UNKNOWN")
        dist = v.get("distance_to_cable_meters", 99999.0)
        cable_name = v.get("nearest_cable", "Submarine Cable")

        risk_detail = risk_service.compute_cable_vessel_risk(
            vessel=v,
            nearest_cable_name=cable_name,
            distance_meters=dist
        )
        risk_results.append({
            "mmsi": mmsi,
            "vessel_name": v.get("name", "UNKNOWN"),
            "lat": v.get("lat"),
            "lon": v.get("lon"),
            "risk_assessment": risk_detail
        })

    risk_results.sort(key=lambda x: x["risk_assessment"]["risk_score"], reverse=True)
    return {
        "total_vessels_assessed": len(risk_results),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "risk_thresholds": {
            "LOW": "0 - 24",
            "MEDIUM": "25 - 49",
            "HIGH": "50 - 74",
            "CRITICAL": "75 - 100"
        },
        "results": risk_results
    }

@app.post("/api/risk/compute")
def compute_single_risk(req: RiskQueryRequest):
    """
    Phase 3 — On-demand explainable risk computation for a single vessel or hypothetical scenario.
    Accepts lat/lon, vessel type, speed, course to compute instant risk score with full breakdown.
    """
    if req.mmsi:
        vessel = ais_service.get_vessel_by_mmsi(req.mmsi)
        if not vessel:
            raise HTTPException(status_code=404, detail=f"MMSI {req.mmsi} not found in active vessel store.")
        dist = vessel.get("distance_to_cable_meters", 99999.0)
        cable_name = vessel.get("nearest_cable", "Submarine Cable")
    elif req.lat is not None and req.lon is not None:
        # Hypothetical position query
        from geo_utils import min_distance_to_cable_geojson
        dist = 99999.0
        cable_name = "Submarine Cable"
        for cable in ais_service.cables_data:
            coords = cable["geometry"]["coordinates"]
            d, _ = min_distance_to_cable_geojson(req.lat, req.lon, coords)
            if d < dist:
                dist = d
                cable_name = cable["properties"]["name"]
        vessel = {
            "name": f"Hypothetical Vessel ({req.lat:.3f}, {req.lon:.3f})",
            "speed": req.speed,
            "course": req.course,
            "heading": req.course,
            "vessel_type": req.vessel_type,
            "loitering_minutes": req.loitering_minutes,
            "data_mode": "HYPOTHETICAL",
            "source_provider": "Manual Query"
        }
    else:
        raise HTTPException(status_code=400, detail="Provide either mmsi or lat+lon coordinates.")

    risk = risk_service.compute_cable_vessel_risk(
        vessel=vessel,
        nearest_cable_name=cable_name,
        distance_meters=dist
    )
    return {"query": req.dict(), "risk_assessment": risk}

@app.get("/api/satellite")
def get_satellite_status():
    """
    Phase 3 — Satellite Intelligence Dashboard:
    Returns current status of Sentinel-1 SAR (primary) and Sentinel-2 Optical (secondary) providers,
    plus all current satellite detections and optical confirmation results.
    """
    detections = dark_vessel_engine.get_all_satellite_detections()
    dark = dark_vessel_engine.get_dark_vessels()

    s1_health = dark_vessel_engine.sentinel1_provider.health_check()
    s2_health = dark_vessel_engine.sentinel2_provider.health_check()

    # Summarise optical confirmation outcomes
    opt_counts = {"OPTICAL_CONFIRMED": 0, "OPTICAL_NOT_CONFIRMED": 0, "OPTICAL_UNAVAILABLE": 0, "INSUFFICIENT_DATA": 0}
    for d in detections:
        status = d.get("optical_confirmation_status", "OPTICAL_UNAVAILABLE")
        if status in opt_counts:
            opt_counts[status] += 1

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "last_scan": dark_vessel_engine.last_scan_timestamp,
        "providers": {
            "sentinel1_sar": s1_health,
            "sentinel2_optical": s2_health
        },
        "detection_summary": {
            "total_detections": len(detections),
            "potential_dark_vessels": len(dark),
            "optical_confirmation_breakdown": opt_counts
        },
        "detections": detections,
        "limitations": [
            "Sentinel-1 IW revisit rate: 1-3 days over cable corridors (non-continuous).",
            "Sentinel-2 optical requires daylight and cloud cover < configured threshold.",
            "POTENTIAL_DARK_VESSEL is a maximum classification; AIS absence alone does not confirm illegal activity.",
            "CA-CFAR pixel detection uses ~20m pixel resolution; vessels < 12m may not produce detectable RCS."
        ]
    }

@app.get("/api/satellite/sentinel2")
def get_sentinel2_status():
    """
    Returns Sentinel-2 optical provider health, current configuration, and limitations.
    """
    s2 = dark_vessel_engine.sentinel2_provider
    return {
        "provider": "Copernicus Sentinel-2 MSI Optical",
        "data_source": "FREE — Copernicus Data Space Ecosystem (CDSE)",
        "url": "https://dataspace.copernicus.eu/",
        "role": "Secondary optical confirmation of Sentinel-1 SAR radar vessel candidates",
        "enabled": s2.enabled,
        "status": s2.last_status,
        "max_cloud_cover_threshold_pct": s2.max_cloud_cover,
        "cached_products": len(s2.cached_products),
        "limitations": [
            "Sentinel-2 is OPTICAL — does not operate at night or through clouds.",
            "Temporal revisit: 5 days at equator (1-2 days with both S2A and S2B satellites).",
            "OPTICAL_NOT_CONFIRMED does NOT prove a vessel is absent — cloud/night/timing may prevent confirmation.",
            "Sentinel-2 is secondary only; Sentinel-1 C-Band SAR remains the primary detection source.",
            "Image download requires Copernicus account credentials for full imagery access."
        ],
        "confirmation_statuses": {
            "OPTICAL_CONFIRMED": "Clear optical scene available, target coordinates validated.",
            "OPTICAL_NOT_CONFIRMED": "Scene available but target signature not confirmed (may be cloud, night, or vessel moved).",
            "OPTICAL_UNAVAILABLE": "No suitable Sentinel-2 scene available within temporal/spatial window.",
            "INSUFFICIENT_DATA": "Cloud cover or data quality too low to draw any conclusion."
        }
    }
