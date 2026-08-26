# backend/services/risk_scoring_service.py
import os
import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("oceanguard.risk_service")

class RiskScoringService:
    """
    Explainable Maritime Submarine Cable Threat Risk Engine.
    Computes an explicit numeric score (0 - 100) based on weighted factors:
    - Distance to cable (35%)
    - Vessel speed & approach vector (20%)
    - Vessel type risk (15%)
    - Loitering duration (10%)
    - Sentinel-1 SAR presence with missing AIS (10%)
    - Sentinel-2 Optical validation (10%)
    
    Provides contributing factors breakdown, textual explanation, and Data Quality ratings.
    """

    def __init__(self):
        # Configurable weights via Environment Variables (Default sum = 1.0)
        self.w_distance = float(os.getenv("WEIGHT_DISTANCE", "0.35"))
        self.w_speed = float(os.getenv("WEIGHT_SPEED_COURSE", "0.20"))
        self.w_type = float(os.getenv("WEIGHT_VESSEL_TYPE", "0.15"))
        self.w_loiter = float(os.getenv("WEIGHT_LOITERING", "0.10"))
        self.w_sar = float(os.getenv("WEIGHT_SAR_DARK", "0.10"))
        self.w_optical = float(os.getenv("WEIGHT_OPTICAL_CONF", "0.10"))

        # Configurable risk thresholds
        self.thresh_medium = float(os.getenv("THRESH_RISK_MEDIUM", "25.0"))
        self.thresh_high = float(os.getenv("THRESH_RISK_HIGH", "50.0"))
        self.thresh_critical = float(os.getenv("THRESH_RISK_CRITICAL", "75.0"))

    def compute_cable_vessel_risk(
        self,
        vessel: Dict[str, Any],
        nearest_cable_name: str,
        distance_meters: float,
        optical_confirmation: Optional[Dict[str, Any]] = None,
        sar_detection: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Computes detailed cable-specific risk evaluation for a vessel or satellite detection.
        """
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        speed = float(vessel.get("speed", 0.0))
        course = float(vessel.get("course", 0.0))
        heading = float(vessel.get("heading", course))
        v_type = str(vessel.get("vessel_type", "Merchant"))
        loiter_mins = float(vessel.get("loitering_minutes", 0.0))
        data_mode = str(vessel.get("data_mode", "REAL_AIS"))
        source_provider = str(vessel.get("source_provider", "AIS Telemetry"))

        # 1. Proximity Sub-Score (0 - 100)
        if distance_meters <= 500:
            sub_dist = 100.0
            zone = "CRITICAL_500M"
        elif distance_meters <= 1000:
            sub_dist = 70.0 + (1000 - distance_meters) / 500.0 * 30.0
            zone = "MONITORING_1KM"
        elif distance_meters <= 5000:
            sub_dist = (5000 - distance_meters) / 4000.0 * 70.0
            zone = "WARNING_5KM"
        else:
            sub_dist = 0.0
            zone = "SAFE_OPEN_SEAS"

        # 2. Speed & Approach Vector Sub-Score (0 - 100)
        # Slow speed near cable (< 3.0 kts) is high risk for anchoring/trawling
        if distance_meters <= 5000:
            if speed <= 1.0:
                sub_speed = 100.0  # Stopped/Anchored
            elif speed <= 3.5:
                sub_speed = 85.0   # Trawling speed
            elif speed <= 6.0:
                sub_speed = 60.0   # Slow maneuver
            elif speed <= 12.0:
                sub_speed = 45.0   # Active approach / transit in cable corridor
            else:
                sub_speed = 20.0   # Fast transit
        else:
            sub_speed = 10.0 if speed <= 3.0 else 0.0

        # Approach direction classification
        if heading >= 0 and heading <= 360:
            approach_dir = f"Heading {heading:.0f}° relative to cable line"
        else:
            approach_dir = "Undetermined Trajectory"

        # 3. Vessel Type Sub-Score (0 - 100)
        v_lower = v_type.lower()
        if any(t in v_lower for t in ["trawler", "fishing", "dredger", "anchor"]):
            sub_type = 100.0
        elif any(t in v_lower for t in ["tug", "barge", "workboat", "research"]):
            sub_type = 70.0
        elif "cable" in v_lower:
            sub_type = 15.0  # Authorized cable ship
        else:
            sub_type = 35.0  # Merchant / Tanker

        # 4. Loitering Sub-Score (0 - 100)
        if distance_meters <= 2000:
            sub_loiter = min(100.0, (loiter_mins / 30.0) * 100.0)
        else:
            sub_loiter = 0.0

        # 5. Sentinel-1 SAR Sub-Score (0 - 100)
        is_dark = sar_detection.get("classification") == "POTENTIAL_DARK_VESSEL" if sar_detection else (vessel.get("potential_dark_vessel", False))
        sub_sar = 90.0 if is_dark else (40.0 if sar_detection else 0.0)

        # 6. Sentinel-2 Optical Confirmation Sub-Score (0 - 100)
        opt_status = optical_confirmation.get("confirmation_status", "OPTICAL_UNAVAILABLE") if optical_confirmation else "OPTICAL_UNAVAILABLE"
        if opt_status == "OPTICAL_CONFIRMED":
            sub_opt = 60.0
        elif opt_status == "OPTICAL_NOT_CONFIRMED":
            sub_opt = 30.0
        else:
            sub_opt = 0.0

        # Weighted Total Score Calculation
        total_score = (
            sub_dist * self.w_distance +
            sub_speed * self.w_speed +
            sub_type * self.w_type +
            sub_loiter * self.w_loiter +
            sub_sar * self.w_sar +
            sub_opt * self.w_optical
        )
        total_score = round(min(100.0, max(0.0, total_score)), 1)

        # Determine Risk Level Category
        if total_score >= self.thresh_critical:
            risk_level = "CRITICAL"
            color = "#DC2626"
        elif total_score >= self.thresh_high:
            risk_level = "HIGH"
            color = "#F59E0B"
        elif total_score >= self.thresh_medium:
            risk_level = "MEDIUM"
            color = "#EAB308"
        else:
            risk_level = "LOW"
            color = "#16A34A"

        # Determine Data Quality Level
        if data_mode == "REAL_AIS" and opt_status == "OPTICAL_CONFIRMED":
            data_quality = "HIGH"
        elif data_mode == "REAL_AIS" or sar_detection:
            data_quality = "MEDIUM"
        elif data_mode == "SIMULATED_TEST":
            data_quality = "LOW"
        else:
            data_quality = "INSUFFICIENT_DATA"

        # Construct Explainable Rationale
        factors = []
        if sub_dist >= 50.0:
            factors.append(f"Proximity: {distance_meters:.0f}m inside {zone}")
        if sub_speed >= 50.0:
            factors.append(f"Speed Anomaly: {speed} kts slow speed near cable")
        if sub_type >= 70.0:
            factors.append(f"High-Risk Type: {v_type}")
        if sub_loiter >= 50.0:
            factors.append(f"Loitering: {loiter_mins:.1f} mins duration")
        if is_dark:
            factors.append("Sentinel-1 SAR Potential Dark Vessel")

        explanation = f"{risk_level} risk score ({total_score}/100) calculated for {vessel.get('name', 'Vessel')} near {nearest_cable_name}. "
        explanation += "Key factors: " + (", ".join(factors) if factors else "Standard transit in safe waters.")

        return {
            "risk_score": total_score,
            "risk_level": risk_level,
            "color": color,
            "nearest_cable": nearest_cable_name,
            "distance_meters": round(distance_meters, 1),
            "zone": zone,
            "approach_direction": approach_dir,
            "speed_knots": speed,
            "course_degrees": course,
            "heading_degrees": heading,
            "ais_status": "AIS_TRANSMITTING" if data_mode == "REAL_AIS" else "NO_AIS_BROADCAST",
            "satellite_status": sar_detection.get("satellite_source", "No Satellite Pass") if sar_detection else "No Satellite Detection",
            "optical_status": opt_status,
            "data_quality": data_quality,
            "contributing_factors": {
                "distance_factor": round(sub_dist * self.w_distance, 1),
                "speed_factor": round(sub_speed * self.w_speed, 1),
                "type_factor": round(sub_type * self.w_type, 1),
                "loitering_factor": round(sub_loiter * self.w_loiter, 1),
                "sar_dark_factor": round(sub_sar * self.w_sar, 1),
                "optical_factor": round(sub_opt * self.w_optical, 1)
            },
            "weights_used": {
                "distance": self.w_distance,
                "speed": self.w_speed,
                "type": self.w_type,
                "loitering": self.w_loiter,
                "sar_dark": self.w_sar,
                "optical": self.w_optical
            },
            "explanation": explanation,
            "timestamp": now_str,
            "data_sources_used": [source_provider] + ([sar_detection["satellite_source"]] if sar_detection else [])
        }
