import time
import random
from typing import List, Dict, Any
from geo_utils import haversine_distance_meters

class DarkVesselEngine:
    def __init__(self):
        self.last_scan_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.dark_vessels: List[Dict[str, Any]] = [
            {
                "id": "DARK-SAR-8921",
                "satellite_source": "Sentinel-1A SAR (C-Band Synthetic Aperture Radar)",
                "acquisition_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 1800)),
                "polarisation": "VV + VH",
                "lat": 38.25,
                "lon": -62.48,  # 2.2 km north of MAREA cable segment
                "estimated_length_m": 78,
                "estimated_beam_m": 14,
                "radar_cross_section_db": 34.2,
                "sar_confidence_score": 0.94,
                "ais_broadcasting": False,
                "threat_assessment": "UNIDENTIFIED VESSEL NEAR MAREA CABLE - NO AIS SIGNAL",
                "distance_to_nearest_cable_m": 1420.0,
                "nearest_cable": "MAREA Cable System",
                "recommended_action": "Dispatch Maritime Patrol Craft & Request Commercial Satellite High-Res Optical Follow-up",
                "status": "UNVERIFIED_TARGET"
            },
            {
                "id": "DARK-SAR-4410",
                "satellite_source": "Sentinel-1B SAR",
                "acquisition_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600)),
                "polarisation": "VV",
                "lat": 24.10,
                "lon": 34.80,  # Red Sea near SEA-ME-WE 5
                "estimated_length_m": 115,
                "estimated_beam_m": 19,
                "radar_cross_section_db": 41.5,
                "sar_confidence_score": 0.88,
                "ais_broadcasting": False,
                "threat_assessment": "DARK TANKER / UNREGISTERED CARRIER IN CABLE PROTECTION ZONE",
                "distance_to_nearest_cable_m": 2100.0,
                "nearest_cable": "SEA-ME-WE 5",
                "recommended_action": "Issue Automatic VHF Warning Broadcast & Alert Regional Naval Command",
                "status": "MONITORED"
            }
        ]

    def get_dark_vessels(self) -> List[Dict[str, Any]]:
        return self.dark_vessels

    def run_satellite_sar_sweep(self, active_ais_vessels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Simulates fresh Sentinel-1 satellite pass over active cable corridors.
        Detects radar returns and cross-references against active AIS broadcasts.
        """
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.last_scan_timestamp = now_str

        # Generate fresh dark vessel candidate
        new_id = f"DARK-SAR-{random.randint(5000, 9999)}"
        # Pick cable corridor
        sar_lat = round(37.52 + random.uniform(-0.1, 0.1), 4)
        sar_lon = round(-71.48 + random.uniform(-0.1, 0.1), 4)

        # Verify no active AIS vessel within 2000m
        ais_match_found = False
        for vessel in active_ais_vessels:
            d = haversine_distance_meters(sar_lat, sar_lon, vessel["lat"], vessel["lon"])
            if d < 2000.0:
                ais_match_found = True
                break

        if not ais_match_found:
            new_target = {
                "id": new_id,
                "satellite_source": "Sentinel-1A SAR (Fresh Satellite Pass)",
                "acquisition_time": now_str,
                "polarisation": "VV + VH",
                "lat": sar_lat,
                "lon": sar_lon,
                "estimated_length_m": random.randint(55, 120),
                "estimated_beam_m": random.randint(10, 22),
                "radar_cross_section_db": round(random.uniform(28.0, 45.0), 1),
                "sar_confidence_score": round(random.uniform(0.85, 0.98), 2),
                "ais_broadcasting": False,
                "threat_assessment": "NEW SATELLITE SAR DETECTED DARK VESSEL",
                "distance_to_nearest_cable_m": round(random.uniform(600.0, 1800.0), 1),
                "nearest_cable": "MAREA Cable System",
                "recommended_action": "Flag for Immediate Coast Guard AIS Interrogation",
                "status": "UNVERIFIED_TARGET"
            }
            self.dark_vessels.insert(0, new_target)
            if len(self.dark_vessels) > 8:
                self.dark_vessels.pop()

        return {
            "status": "SUCCESS",
            "satellite": "Sentinel-1A SAR",
            "sweep_timestamp": now_str,
            "detected_targets": len(self.dark_vessels),
            "dark_vessels": self.dark_vessels
        }
