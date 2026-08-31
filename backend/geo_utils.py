import math
from typing import List, Tuple, Dict, Any

# Earth radius in kilometers
EARTH_RADIUS_KM = 6371.0088

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth in meters.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return EARTH_RADIUS_KM * c * 1000.0


def point_to_line_segment_distance_meters(
    p_lat: float, p_lon: float, 
    a_lat: float, a_lon: float, 
    b_lat: float, b_lon: float
) -> float:
    """
    Calculate minimum distance in meters from point P to line segment AB.
    Uses equirectangular planar projection approximation for localized segments,
    which is accurate for distances up to a few hundred km.
    """
    # Convert lat/lon degrees to meters relative to A
    cos_lat = math.cos(math.radians(a_lat))
    
    # Point P relative to A
    px = (p_lon - a_lon) * 111320.0 * cos_lat
    py = (p_lat - a_lat) * 110540.0

    # Point B relative to A
    bx = (b_lon - a_lon) * 111320.0 * cos_lat
    by = (b_lat - a_lat) * 110540.0

    # Vector AB length squared
    ab2 = bx * bx + by * by

    if ab2 < 1e-6:
        # A and B are effectively the same point
        return math.sqrt(px * px + py * py)

    # Projection factor t of P onto line AB
    t = max(0.0, min(1.0, (px * bx + py * by) / ab2))

    # Nearest point on segment
    nx = t * bx
    ny = t * by

    # Distance from P to nearest point N
    dx = px - nx
    dy = py - ny

    return math.sqrt(dx * dx + dy * dy)


def min_distance_to_cable_geojson(vessel_lat: float, vessel_lon: float, cable_geojson_coords: List[List[float]]) -> Tuple[float, List[float]]:
    """
    Finds the minimum distance in meters from a vessel position to a polyline cable coordinates [lon, lat].
    Returns (min_distance_meters, nearest_point_[lat, lon])
    """
    min_dist = float('inf')
    nearest_pt = [vessel_lat, vessel_lon]

    for i in range(len(cable_geojson_coords) - 1):
        lon1, lat1 = cable_geojson_coords[i][0], cable_geojson_coords[i][1]
        lon2, lat2 = cable_geojson_coords[i+1][0], cable_geojson_coords[i+1][1]

        d = point_to_line_segment_distance_meters(
            vessel_lat, vessel_lon,
            lat1, lon1,
            lat2, lon2
        )

        if d < min_dist:
            min_dist = d

    return min_dist, nearest_pt


def calculate_ai_risk_score(
    distance_meters: float,
    speed_knots: float,
    vessel_type: str,
    loitering_minutes: float = 0.0,
    course_change_deg: float = 0.0
) -> Dict[str, Any]:
    """
    Calculates AI Risk Score (0 - 100) based on maritime threat models:
    - Distance from Submarine Cable (5000m zone, 1000m zone, 500m critical)
    - Vessel Speed (Slow speeds < 3.0 knots suggest anchor dragging/trawling/loitering)
    - Vessel Type Risk Factor (Fishing Trawlers, Dredgers, Tugboats have higher risk)
    - Loitering Duration inside 1km zone
    """
    # 1. Distance Risk Score (0 - 45 pts)
    if distance_meters <= 500:
        # Linear scaling from 500m (30 pts) to 0m (45 pts)
        dist_score = 30 + (1 - distance_meters / 500.0) * 15.0
    elif distance_meters <= 1000:
        # 1000m to 500m: 15 to 30 pts
        dist_score = 15 + (1 - (distance_meters - 500.0) / 500.0) * 15.0
    elif distance_meters <= 5000:
        # 5000m to 1000m: 0 to 15 pts
        dist_score = (1 - (distance_meters - 1000.0) / 4000.0) * 15.0
    else:
        dist_score = 0.0

    # 2. Speed Risk Score (0 - 25 pts)
    # Slow speed near cable (< 3 knots) is high risk for anchoring/trawling
    if distance_meters <= 2000:
        if speed_knots <= 1.0:
            speed_score = 25.0  # Stopped/Anchored
        elif speed_knots <= 3.5:
            speed_score = 20.0  # Trawling/Dragging speed
        elif speed_knots <= 6.0:
            speed_score = 12.0  # Slow maneuver
        else:
            speed_score = 2.0   # Normal transit speed
    else:
        speed_score = 0.0

    # 3. Vessel Type Multiplier (0 - 15 pts)
    v_type_lower = vessel_type.lower()
    if any(t in v_type_lower for t in ["trawler", "fishing", "dredger", "anchor"]):
        type_score = 15.0
    elif any(t in v_type_lower for t in ["tug", "barge", "workboat", "research"]):
        type_score = 10.0
    elif "cable" in v_type_lower:
        type_score = 2.0  # Authorized cable maintenance ship
    else:
        type_score = 5.0  # Cargo / Tanker

    # 4. Loitering Risk (0 - 15 pts)
    # minutes spent in proximity
    if distance_meters <= 1500:
        loiter_score = min(15.0, (loitering_minutes / 20.0) * 15.0)
    else:
        loiter_score = 0.0

    total_score = round(dist_score + speed_score + type_score + loiter_score, 1)
    total_score = min(100.0, max(0.0, total_score))

    # Risk Category
    if total_score >= 81:
        category = "CRITICAL"
        color = "#EF4444" # Red
    elif total_score >= 61:
        category = "HIGH"
        color = "#F97316" # Orange
    elif total_score >= 31:
        category = "MEDIUM"
        color = "#EAB308" # Yellow
    else:
        category = "LOW"
        color = "#10B981" # Green

    # Determine Geofence Zone
    if distance_meters <= 500:
        zone = "CRITICAL_500M"
    elif distance_meters <= 1000:
        zone = "MONITORING_1KM"
    elif distance_meters <= 5000:
        zone = "WARNING_5KM"
    else:
        zone = "SAFE_OPEN_SEAS"

    contributing_factors = {
        "distance_score": round(dist_score, 1),
        "speed_score": round(speed_score, 1),
        "vessel_type_score": round(type_score, 1),
        "loitering_score": round(loiter_score, 1)
    }
    return {
        # Canonical field names (RiskScoringService schema)
        "risk_score": total_score,
        "risk_level": category,
        "contributing_factors": contributing_factors,
        "color": color,
        "zone": zone,
        # Backward-compatible aliases
        "score": total_score,
        "category": category,
        "breakdown": contributing_factors,
    }
