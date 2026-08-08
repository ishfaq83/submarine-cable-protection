import time
from typing import List, Dict, Any, Optional

class AlertService:
    def __init__(self):
        self.alerts: List[Dict[str, Any]] = [
            {
                "id": "ALT-901",
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
                "trigger_reason": "Vessel inside 500m Critical Zone moving at trawling speed (2.1 kts) with 22m loitering duration.",
                "recommended_action": "Issue Urgent VHF Channel 16 warning to halt trawling & dispatch naval patrol craft immediately.",
                "acknowledged": False,
                "notification_channels_sent": ["Dashboard", "Email", "SMS API"]
            },
            {
                "id": "ALT-884",
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
                "trigger_reason": "Dredger operating within 1km cable buffer zone with low speed.",
                "recommended_action": "Contact port authority to confirm dredging permits along cable corridor.",
                "acknowledged": True,
                "notification_channels_sent": ["Dashboard", "Email"]
            }
        ]

    def evaluate_vessel_alerts(self, vessels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scans current vessel states and generates dynamic alerts for vessels in warning/monitoring/critical zones.
        """
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        for v in vessels:
            mmsi = v.get("mmsi")
            dist = v.get("distance_to_cable_meters", 99999)
            risk = v.get("risk_assessment", {})
            score = risk.get("score", 0)
            category = risk.get("category", "LOW")
            zone = risk.get("zone", "SAFE_OPEN_SEAS")

            # Check if alert already active for this MMSI recently
            existing = next((a for a in self.alerts if a["vessel_mmsi"] == mmsi and not a["acknowledged"]), None)

            if category in ["CRITICAL", "HIGH"] and dist <= 5000:
                if not existing:
                    # Construct Action Recommendation based on speed and distance
                    speed = v.get("speed", 0)
                    if dist <= 500:
                        rec = "CRITICAL ALERT: Contact vessel on VHF Channel 16 immediately. Warn against anchor deployment/trawling. Dispatch fast interceptor vessel."
                    elif dist <= 1000:
                        rec = "MONITORING ALERT: Interrogate AIS destination and monitor speed/heading vector closely."
                    else:
                        rec = "WARNING ALERT: Track vessel progression through 5km protection corridor."

                    new_alert = {
                        "id": f"ALT-{int(time.time()) % 100000}",
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
                        "trigger_reason": f"Vessel entered {zone} zone at {speed} knots (Risk Score: {score}/100)",
                        "recommended_action": rec,
                        "acknowledged": False,
                        "notification_channels_sent": ["Dashboard", "Email", "SMS API"]
                    }
                    self.alerts.insert(0, new_alert)
                    if len(self.alerts) > 20:
                        self.alerts.pop()

        return self.alerts

    def acknowledge_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        for a in self.alerts:
            if a["id"] == alert_id:
                a["acknowledged"] = True
                return a
        return None
