import json
import math
import random
import time
from typing import List, Dict, Any, Optional
from geo_utils import min_distance_to_cable_geojson, calculate_ai_risk_score

class AISTrackerService:
    def __init__(self, cables_geojson_path: str):
        self.cables_data = self._load_cables(cables_geojson_path)
        self.vessels: Dict[str, Dict[str, Any]] = {}
        self.track_history: Dict[str, List[List[float]]] = {}
        self.simulation_running = True
        self.last_update_time = time.time()

        # Initialize fleet of 20+ realistic vessels around cable corridors
        self._init_default_fleet()

    def _load_cables(self, path: str) -> List[Dict[str, Any]]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("features", [])

    def _init_default_fleet(self):
        # Default vessel templates near North Atlantic and Mediterranean cable lines
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
                "loitering_minutes": 0.0
            },
            {
                "mmsi": "224567890",
                "imo": "IMO9723412",
                "name": "OCEAN STAR",
                "vessel_type": "Oil Tanker",
                "flag": "Panama",
                "lat": 43.10,
                "lon": -10.50,
                "speed": 14.2,
                "heading": 210.0,
                "course": 210.0,
                "loitering_minutes": 0.0
            },
            {
                "mmsi": "225987123",
                "imo": "IMO9123456",
                "name": "CANTABRIA TRAWLER",
                "vessel_type": "Fishing Trawler",
                "flag": "Spain",
                "lat": 43.45,
                "lon": -3.20,
                "speed": 2.1,  # Slow trawling speed near MAREA cable landing
                "heading": 310.0,
                "course": 305.0,
                "loitering_minutes": 22.0
            },
            {
                "mmsi": "311002345",
                "imo": "IMO9551122",
                "name": "WAVE HUNTER",
                "vessel_type": "Research Vessel",
                "flag": "Bahamas",
                "lat": 49.20,
                "lon": -14.20,
                "speed": 8.0,
                "heading": 90.0,
                "course": 92.0,
                "loitering_minutes": 5.0
            },
            {
                "mmsi": "232119988",
                "imo": "IMO9348877",
                "name": "CABLE INNOVA",
                "vessel_type": "Cable Maintenance Ship",
                "flag": "UK",
                "lat": 50.50,
                "lon": -5.20,
                "speed": 1.2,
                "heading": 180.0,
                "course": 180.0,
                "loitering_minutes": 45.0
            },
            {
                "mmsi": "413889001",
                "imo": "IMO9661234",
                "name": "DRAGON EXPRESS",
                "vessel_type": "Cargo Vessel",
                "flag": "China",
                "lat": 35.80,
                "lon": 125.00,
                "speed": 19.8,
                "heading": 110.0,
                "course": 110.0,
                "loitering_minutes": 0.0
            },
            {
                "mmsi": "247112233",
                "imo": "IMO9223344",
                "name": "MEDITERRANEAN EXPLORER",
                "vessel_type": "Dredger",
                "flag": "Italy",
                "lat": 37.90,
                "lon": 13.80,
                "speed": 1.5,
                "heading": 45.0,
                "course": 45.0,
                "loitering_minutes": 38.0
            },
            {
                "mmsi": "368991122",
                "imo": "IMO9001122",
                "name": "CHESAPEAKE TUG",
                "vessel_type": "Tugboat",
                "flag": "USA",
                "lat": 36.90,
                "lon": -75.80,
                "speed": 3.8,
                "heading": 100.0,
                "course": 105.0,
                "loitering_minutes": 15.0
            }
        ]

        for v in initial_fleet:
            mmsi = v["mmsi"]
            self.vessels[mmsi] = v
            # Seed position history
            lat, lon = v["lat"], v["lon"]
            self.track_history[mmsi] = [
                [round(lat - 0.08 * (i / 5.0), 4), round(lon - 0.08 * (i / 5.0), 4)]
                for i in range(10, 0, -1)
            ] + [[lat, lon]]

    def step_simulation(self):
        """
        Advances all vessel positions based on speed and heading.
        Recalculates nearest submarine cable distances & risk scores.
        """
        if not self.simulation_running:
            return

        now = time.time()
        dt = min(3.0, now - self.last_update_time)  # cap delta time
        self.last_update_time = now

        for mmsi, v in list(self.vessels.items()):
            speed_kts = v["speed"]
            heading = v["heading"]

            # Convert knots to approx lat/lon delta
            # 1 knot = 1.852 km/h
            distance_km = (speed_kts * 1.852) * (dt / 3600.0) * 15.0  # speed multiplier for smooth UI animation

            # Calculate new position
            rad = math.radians(heading)
            delta_lat = (distance_km * math.cos(rad)) / 111.0
            delta_lon = (distance_km * math.sin(rad)) / (111.0 * max(0.2, math.cos(math.radians(v["lat"]))))

            # Add slight jitter for realism
            delta_lat += random.uniform(-0.0002, 0.0002)
            delta_lon += random.uniform(-0.0002, 0.0002)

            v["lat"] = round(v["lat"] + delta_lat, 5)
            v["lon"] = round(v["lon"] + delta_lon, 5)

            # Update loitering minutes if slow near cables
            if speed_kts < 3.5:
                v["loitering_minutes"] += (dt / 60.0) * 2.0
            else:
                v["loitering_minutes"] = max(0.0, v["loitering_minutes"] - 0.1)

            # Append track history
            if mmsi not in self.track_history:
                self.track_history[mmsi] = []
            self.track_history[mmsi].append([v["lat"], v["lon"]])
            if len(self.track_history[mmsi]) > 40:
                self.track_history[mmsi].pop(0)

            # Compute Spatial Distance to nearest cable
            closest_cable_name = "None"
            min_dist = float('inf')

            for cable in self.cables_data:
                coords = cable["geometry"]["coordinates"]
                cable_name = cable["properties"]["name"]
                dist, _ = min_distance_to_cable_geojson(v["lat"], v["lon"], coords)

                if dist < min_dist:
                    min_dist = dist
                    closest_cable_name = cable_name

            v["nearest_cable"] = closest_cable_name
            v["distance_to_cable_meters"] = round(min_dist, 1)

            # Calculate AI Risk Assessment
            risk = calculate_ai_risk_score(
                distance_meters=min_dist,
                speed_knots=v["speed"],
                vessel_type=v["vessel_type"],
                loitering_minutes=v["loitering_minutes"]
            )
            v["risk_assessment"] = risk

    def get_all_vessels(self) -> List[Dict[str, Any]]:
        self.step_simulation()
        return list(self.vessels.values())

    def get_vessel_by_mmsi(self, mmsi: str) -> Optional[Dict[str, Any]]:
        return self.vessels.get(mmsi)

    def get_vessel_history(self, mmsi: str) -> List[List[float]]:
        return self.track_history.get(mmsi, [])

    def inject_suspicious_vessel(self) -> Dict[str, Any]:
        """
        Injects a high-risk suspicious vessel directly into MAREA cable 500m zone.
        """
        mmsi = f"999{random.randint(10000, 99999)}"
        suspicious_vessel = {
            "mmsi": mmsi,
            "imo": f"IMO99{random.randint(1000, 9999)}",
            "name": "SUSPICIOUS TRAWLER X",
            "vessel_type": "Deep Sea Trawler",
            "flag": "Unknown / Unflagged",
            "lat": 37.51,  # Near MAREA Cable segment
            "lon": -71.49,
            "speed": 1.1,  # Anchor dragging / seabed scraping speed
            "heading": 45.0,
            "course": 45.0,
            "loitering_minutes": 35.0
        }
        self.vessels[mmsi] = suspicious_vessel
        self.track_history[mmsi] = [
            [37.49, -71.53],
            [37.50, -71.51],
            [37.51, -71.49]
        ]
        self.step_simulation()
        return self.vessels[mmsi]
