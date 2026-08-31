# backend/services/alert_service.py
import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("oceanguard.alerts")

class AlertService:
    """
    Structured Maritime Threat Alert & Notification Engine for OceanGuard AI.
    Generates evidence-backed structured alerts for:
    - CABLE_APPROACH & MONITORING_ZONE_INTRUSION
    - POTENTIAL_DARK_VESSEL & POTENTIAL_DARK_VESSEL_NEAR_CABLE
    - SUSPICIOUS_AIS_GAP
    - HIGH_RISK_CABLE_ACTIVITY & CRITICAL_CABLE_ACTIVITY
    """

    def __init__(self):
        self.alerts: List[Dict[str, Any]] = [
            {
                "id": "ALT-901",
                "alert_type": "CRITICAL_CABLE_ACTIVITY",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 300)),
                "vessel_mmsi": "225987123",
                "vessel_name": "CANTABRIA TRAWLER",
                "vessel_type": "Fishing Trawler",
                "location": {"lat": 43.45, "lon": -3.20},
                "nearest_cable": "MAREA Cable System",
                "distance_meters": 480.0,
                "speed_knots": 2.1,
                "risk_level": "CRITICAL",
                "risk_score": 88.5,
                "zone": "CRITICAL_500M",
                "data_quality": "HIGH",
                "trigger_reason": "Vessel inside 500m Critical Zone moving at trawling speed (2.1 kts) with 22m loitering duration.",
                "evidence": {
                    "distance_meters": 480.0,
                    "speed_knots": 2.1,
                    "loitering_minutes": 22.0,
                    "vessel_type": "Fishing Trawler"
                },
                "recommended_action": "Issue Urgent VHF Channel 16 warning to halt trawling & dispatch naval patrol craft immediately.",
                "acknowledged": False,
                "notification_channels_sent": ["Dashboard", "Email", "SMS API"]
            },
            {
                "id": "ALT-884",
                "alert_type": "MONITORING_ZONE_INTRUSION",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 1200)),
                "vessel_mmsi": "247112233",
                "vessel_name": "MEDITERRANEAN EXPLORER",
                "vessel_type": "Dredger",
                "location": {"lat": 37.90, "lon": 13.80},
                "nearest_cable": "SEA-ME-WE 5",
                "distance_meters": 950.0,
                "speed_knots": 1.5,
                "risk_level": "HIGH",
                "risk_score": 68.0,
                "zone": "MONITORING_1KM",
                "data_quality": "HIGH",
                "trigger_reason": "Dredger operating within 1km cable buffer zone with low speed.",
                "evidence": {
                    "distance_meters": 950.0,
                    "speed_knots": 1.5,
                    "vessel_type": "Dredger"
                },
                "recommended_action": "Contact port authority to confirm dredging permits along cable corridor.",
                "acknowledged": True,
                "notification_channels_sent": ["Dashboard", "Email"]
            }
        ]

    def evaluate_vessel_alerts(self, vessels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scans active vessels and generates evidence-backed alerts.
        """
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        for v in vessels:
            mmsi = v.get("mmsi")
            dist = v.get("distance_to_cable_meters", 99999)
            risk = v.get("risk_assessment", {})
            # Use canonical RiskScoringService field names; fall back to old aliases for safety
            score = risk.get("risk_score", risk.get("score", 0))
            category = risk.get("risk_level", risk.get("category", "LOW"))
            zone = risk.get("zone", "SAFE_OPEN_SEAS")

            existing = next((a for a in self.alerts if a.get("vessel_mmsi") == mmsi and not a["acknowledged"]), None)

            if category in ["CRITICAL", "HIGH"] and dist <= 5000:
                if not existing:
                    speed = v.get("speed", 0)

                    if category == "CRITICAL":
                        alert_type = "CRITICAL_CABLE_ACTIVITY"
                        rec = "CRITICAL ALERT: Contact vessel on VHF Channel 16 immediately. Warn against anchor deployment/trawling. Dispatch fast interceptor vessel."
                    elif dist <= 500:
                        alert_type = "CABLE_APPROACH"
                        rec = "CABLE APPROACH: Monitor vessel heading trajectory towards 500m protection zone."
                    elif dist <= 1000:
                        alert_type = "MONITORING_ZONE_INTRUSION"
                        rec = "MONITORING ALERT: Interrogate AIS destination and monitor speed/heading vector closely."
                    else:
                        alert_type = "HIGH_RISK_CABLE_ACTIVITY"
                        rec = "WARNING ALERT: Track vessel progression through 5km protection corridor."

                    new_alert = {
                        "id": f"ALT-{int(time.time() * 1000) % 100000}",
                        "alert_type": alert_type,
                        "timestamp": now_str,
                        "vessel_mmsi": mmsi,
                        "vessel_name": v.get("name", "UNKNOWN"),
                        "vessel_type": v.get("vessel_type", "Vessel"),
                        "location": {"lat": v.get("lat"), "lon": v.get("lon")},
                        "nearest_cable": v.get("nearest_cable", "Submarine Cable"),
                        "distance_meters": dist,
                        "speed_knots": speed,
                        "risk_level": category,
                        "risk_score": score,
                        "zone": zone,
                        "data_quality": v.get("data_quality", "MEDIUM"),
                        "trigger_reason": f"{alert_type}: Vessel inside {zone} at {speed} kts (Risk Score: {score}/100)",
                        "evidence": {
                            "distance_meters": dist,
                            "speed_knots": speed,
                            "loitering_minutes": v.get("loitering_minutes", 0.0),
                            "risk_breakdown": risk.get("contributing_factors", risk.get("breakdown", {}))
                        },
                        "recommended_action": rec,
                        "acknowledged": False,
                        "notification_channels_sent": ["Dashboard", "Email", "SMS API"]
                    }
                    self.alerts.insert(0, new_alert)
                    if len(self.alerts) > 30:
                        self.alerts.pop()

        return self.alerts

    def evaluate_satellite_alerts(self, satellite_detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generates alerts for POTENTIAL_DARK_VESSEL and POTENTIAL_DARK_VESSEL_NEAR_CABLE.
        """
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        for det in satellite_detections:
            if det.get("classification") != "POTENTIAL_DARK_VESSEL":
                continue

            target_id = det.get("id")
            existing = next((a for a in self.alerts if a.get("target_id") == target_id and not a["acknowledged"]), None)

            if not existing:
                cable_dist = det.get("distance_to_nearest_cable_m", 99999.0)
                is_near_cable = det.get("inside_monitoring_zone", False) or cable_dist <= 5000.0

                alert_type = "POTENTIAL_DARK_VESSEL_NEAR_CABLE" if is_near_cable else "POTENTIAL_DARK_VESSEL"
                risk_level = "CRITICAL" if cable_dist <= 1000.0 else ("HIGH" if is_near_cable else "MEDIUM")

                new_alert = {
                    "id": f"ALT-SAR-{int(time.time() * 1000) % 100000}",
                    "alert_type": alert_type,
                    "target_id": target_id,
                    "timestamp": now_str,
                    "vessel_mmsi": "NO_AIS_BROADCAST",
                    "vessel_name": f"POTENTIAL DARK TARGET ({det.get('id')})",
                    "vessel_type": "Unidentified Radar Contact",
                    "location": {"lat": det.get("lat"), "lon": det.get("lon")},
                    "nearest_cable": det.get("nearest_cable", "Submarine Cable"),
                    "distance_meters": cable_dist,
                    "speed_knots": 0.0,
                    "risk_level": risk_level,
                    "risk_score": 85.0 if is_near_cable else 65.0,
                    "zone": "CRITICAL_500M" if cable_dist <= 500 else ("MONITORING_1KM" if cable_dist <= 1000 else "WARNING_5KM"),
                    "data_quality": det.get("data_quality", "MEDIUM"),
                    "trigger_reason": det.get("rationale", "Sentinel-1 SAR detected vessel candidate without matching AIS broadcast."),
                    "evidence": {
                        "primary_satellite": det.get("primary_satellite_source", det.get("satellite_source", "Sentinel-1 SAR")),
                        "secondary_optical": det.get("secondary_optical_source", "Sentinel-2 MSI"),
                        "optical_confirmation": det.get("optical_confirmation_status"),
                        "sentinel1_product_id": det.get("sentinel1_product_id"),
                        "sentinel2_product_id": det.get("sentinel2_product_id")
                    },
                    "satellite_metadata": {
                        "satellite_source": det.get("primary_satellite_source", det.get("satellite_source", "Sentinel-1 SAR")),
                        "sentinel1_product_id": det.get("sentinel1_product_id"),
                        "sentinel2_product_id": det.get("sentinel2_product_id"),
                        "sar_confidence_score": det.get("sar_confidence_score", 0.90),
                        "optical_confirmation_status": det.get("optical_confirmation_status"),
                        "acquisition_timestamp": det.get("acquisition_timestamp"),
                        "processing_timestamp": det.get("processing_timestamp")
                    },
                    "recommended_action": det.get("recommended_action", "Dispatch Maritime Patrol Verification Craft & Request High-Res Optical Follow-up."),
                    "acknowledged": False,
                    "notification_channels_sent": ["Dashboard", "Satellite Threat Alert API"]
                }
                self.alerts.insert(0, new_alert)
                if len(self.alerts) > 30:
                    self.alerts.pop()

        return self.alerts

    def acknowledge_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        for a in self.alerts:
            if a["id"] == alert_id:
                a["acknowledged"] = True
                return a
        return None
