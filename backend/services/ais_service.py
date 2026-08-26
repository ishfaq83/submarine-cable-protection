# backend/services/ais_service.py
import os
import json
import math
import random
import time
import logging
from typing import List, Dict, Any, Optional

from geo_utils import min_distance_to_cable_geojson, calculate_ai_risk_score
from providers.ais_adapter import get_active_ais_providers, BaseAISProvider

logger = logging.getLogger("oceanguard.ais_service")

class AISTrackerService:
    """
    Core AIS Tracker Service for OceanGuard AI.
    Routes live vessel telemetry from modular real-world AIS providers (Digitraffic, AISStream)
    into spatial cable geofencing and AI risk calculation engines.
    """

    def __init__(self, cables_geojson_path: str):
        self.cables_data = self._load_cables(cables_geojson_path)
        self.vessels: Dict[str, Dict[str, Any]] = {}
        self.track_history: Dict[str, List[List[float]]] = {}

        # Load modular real-world AIS providers
        self.providers: List[BaseAISProvider] = get_active_ais_providers()

        # Simulator Fallback configuration (Disabled by default in production)
        self.use_simulator_fallback = os.getenv("USE_SIMULATOR_FALLBACK", "false").lower() in ["true", "1", "yes"]
        self.simulation_running = False
        self.last_update_time = time.time()

        if self.use_simulator_fallback:
            logger.info("USE_SIMULATOR_FALLBACK enabled: Initializing dev/testing simulation fleet.")
            self._init_simulator_fleet()

    def _load_cables(self, path: str) -> List[Dict[str, Any]]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("features", [])
        except Exception as e:
            logger.error(f"Failed to load submarine cables GeoJSON from {path}: {e}")
            return []

    def get_all_vessels(self) -> List[Dict[str, Any]]:
        """
        Production Data Path: Queries active real-world AIS providers, processes spatial cable distance,
        and computes AI risk scores.
        """
        real_vessels_found = False
        updated_fleet: Dict[str, Dict[str, Any]] = {}

        # 1. Poll Real AIS Providers
        for provider in self.providers:
            try:
                raw_vessels = provider.fetch_vessels()
                if raw_vessels:
                    real_vessels_found = True
                    for v in raw_vessels:
                        mmsi = v["mmsi"]
                        self._enrich_vessel_spatial_data(v)
                        updated_fleet[mmsi] = v
                        self._update_track_history(mmsi, v["lat"], v["lon"])
            except Exception as e:
                logger.error(f"Error querying provider {provider.provider_name}: {e}")

        if real_vessels_found:
            self.vessels = updated_fleet
            return list(self.vessels.values())

        # 2. Production Rule: If real data is active, return current vessel store (do not generate fake data)
        if not self.use_simulator_fallback:
            return list(self.vessels.values())

        # 3. Development/Testing Fallback Only (Explicitly tagged as SIMULATED_TEST)
        self._step_simulator_fallback()
        return list(self.vessels.values())

    def _enrich_vessel_spatial_data(self, v: Dict[str, Any]):
        """
        Computes geodesic distance to nearest submarine cable and calculates AI risk score.
        """
        lat, lon = v["lat"], v["lon"]
        speed = v.get("speed", 0.0)
        vessel_type = v.get("vessel_type", "Merchant")
        loitering_mins = v.get("loitering_minutes", 0.0)

        # Compute Spatial Distance to nearest cable
        closest_cable_name = "None"
        min_dist = float('inf')

        for cable in self.cables_data:
            coords = cable["geometry"]["coordinates"]
            cable_name = cable["properties"]["name"]
            dist, _ = min_distance_to_cable_geojson(lat, lon, coords)

            if dist < min_dist:
                min_dist = dist
                closest_cable_name = cable_name

        v["nearest_cable"] = closest_cable_name
        v["distance_to_cable_meters"] = round(min_dist, 1)

        # Calculate AI Risk Assessment
        risk = calculate_ai_risk_score(
            distance_meters=min_dist,
            speed_knots=speed,
            vessel_type=vessel_type,
            loitering_minutes=loitering_mins
        )
        v["risk_assessment"] = risk

    def _update_track_history(self, mmsi: str, lat: float, lon: float):
        """Maintains position history buffer for track trails."""
        if mmsi not in self.track_history:
            self.track_history[mmsi] = []
        self.track_history[mmsi].append([lat, lon])
        if len(self.track_history[mmsi]) > 40:
            self.track_history[mmsi].pop(0)

    def get_vessel_by_mmsi(self, mmsi: str) -> Optional[Dict[str, Any]]:
        return self.vessels.get(mmsi)

    def get_vessel_history(self, mmsi: str) -> List[List[float]]:
        return self.track_history.get(mmsi, [])

    def get_provider_status(self) -> List[Dict[str, Any]]:
        """Returns provider status list for diagnostic monitoring."""
        status_list = []
        for p in self.providers:
            status_list.append(p.health_check())
        if self.use_simulator_fallback:
            status_list.append({
                "provider": "Development Simulator Fallback",
                "real_data": False,
                "coverage": "Synthetic Test Fleet",
                "status": "ACTIVE_FALLBACK"
            })
        return status_list

    # =========================================================================
    # ISOLATED DEVELOPMENT / TESTING SIMULATOR FALLBACK (DISABLED IN PRODUCTION)
    # =========================================================================

    def _init_simulator_fleet(self):
        initial_fleet = [
            {
                "mmsi": "367123450",
                "imo": "IMO9812341",
                "name": "ATLANTIC MARINER",
                "vessel_type": "Container Ship",
                "flag": "USA",
                "lat": 38.20,
                "lon": -62.50,
                "speed": 18.5,
                "heading": 75.0,
                "course": 75.0,
                "loitering_minutes": 0.0,
                "source_provider": "Development Simulator Fallback",
                "data_mode": "SIMULATED_TEST",
                "coverage_info": "Synthetic Test Fleet"
            },
            {
                "mmsi": "225987123",
                "imo": "IMO9123456",
                "name": "CANTABRIA TRAWLER",
                "vessel_type": "Fishing Trawler",
                "flag": "Spain",
                "lat": 43.45,
                "lon": -3.20,
                "speed": 2.1,
                "heading": 310.0,
                "course": 305.0,
                "loitering_minutes": 22.0,
                "source_provider": "Development Simulator Fallback",
                "data_mode": "SIMULATED_TEST",
                "coverage_info": "Synthetic Test Fleet"
            }
        ]
        for v in initial_fleet:
            mmsi = v["mmsi"]
            self._enrich_vessel_spatial_data(v)
            self.vessels[mmsi] = v
            self._update_track_history(mmsi, v["lat"], v["lon"])

    def _step_simulator_fallback(self):
        now = time.time()
        dt = min(3.0, now - self.last_update_time)
        self.last_update_time = now

        for mmsi, v in list(self.vessels.items()):
            speed_kts = v["speed"]
            heading = v["heading"]
            distance_km = (speed_kts * 1.852) * (dt / 3600.0) * 15.0
            rad = math.radians(heading)
            delta_lat = (distance_km * math.cos(rad)) / 111.0
            delta_lon = (distance_km * math.sin(rad)) / (111.0 * max(0.2, math.cos(math.radians(v["lat"]))))

            v["lat"] = round(v["lat"] + delta_lat, 5)
            v["lon"] = round(v["lon"] + delta_lon, 5)
            self._enrich_vessel_spatial_data(v)
            self._update_track_history(mmsi, v["lat"], v["lon"])

    def inject_suspicious_vessel(self) -> Dict[str, Any]:
        """
        Injects a test vessel directly into MAREA cable 500m zone for demo/testing.
        Explicitly tagged as SIMULATED_TEST data_mode.
        """
        mmsi = f"999{random.randint(10000, 99999)}"
        suspicious_vessel = {
            "mmsi": mmsi,
            "imo": f"IMO99{random.randint(1000, 9999)}",
            "name": "TEST DEMO TRAWLER",
            "vessel_type": "Deep Sea Trawler",
            "flag": "Demo Test Target",
            "lat": 37.51,
            "lon": -71.49,
            "speed": 1.1,
            "heading": 45.0,
            "course": 45.0,
            "loitering_minutes": 35.0,
            "source_provider": "Demo Injector",
            "data_mode": "SIMULATED_TEST",
            "coverage_info": "Injected Threat Simulation"
        }
        self._enrich_vessel_spatial_data(suspicious_vessel)
        self.vessels[mmsi] = suspicious_vessel
        self._update_track_history(mmsi, 37.51, -71.49)
        return self.vessels[mmsi]
