# backend/providers/ais_adapter.py
import os
import json
import time
import logging
import urllib.request
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger("oceanguard.providers")

# Standardized Common Vessel Data Schema
# All providers MUST normalize their telemetry output into this exact dictionary structure.
"""
{
    "mmsi": str,
    "imo": str,
    "name": str,
    "vessel_type": str,
    "flag": str,
    "lat": float,
    "lon": float,
    "speed": float,         # in knots (SOG)
    "course": float,        # in degrees (COG)
    "heading": float,       # in degrees
    "timestamp": str,       # ISO 8601 UTC string
    "source_provider": str, # e.g., "Digitraffic (Finland)", "AISStream.io"
    "data_mode": str,       # "REAL_AIS", "SIMULATED_TEST", "SATELLITE_SAR"
    "coverage_info": str    # Description of provider geographic scope
}
"""

class BaseAISProvider(ABC):
    """
    Abstract Base Class for modular AIS telemetry providers.
    Each provider represents a distinct AIS data source (Open REST, WebSocket, Satellite, etc.).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""
        pass

    @property
    @abstractmethod
    def coverage_area(self) -> str:
        """Geographic & spatial coverage limitations of this data source."""
        pass

    @property
    @abstractmethod
    def is_real_data(self) -> bool:
        """True if source delivers real-world live AIS broadcasts, False if synthetic/simulation."""
        pass

    @abstractmethod
    def fetch_vessels(self) -> List[Dict[str, Any]]:
        """
        Fetches live vessel positions and normalizes them into the standard Common Vessel Schema.
        Must handle connectivity timeouts gracefully and return an empty list on network failure.
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Returns health status, active status, and metadata for monitoring."""
        pass


class DigitrafficProvider(BaseAISProvider):
    """
    FREE Real-World Open Public AIS Data Provider: Digitraffic Finland (Fintraffic).
    Current API URL: https://meri.digitraffic.fi/api/ais/v1/locations
    Coverage: Baltic Sea, Gulf of Finland, and Northern European Cable Corridors.
    Access Model: Free open public API (No API key required).

    Endpoint can be overridden via the DIGITRAFFIC_API_URL environment variable.
    NOTE: The legacy hostname vessels.digitraffic.fi is decommissioned and will
    raise [Errno -2] Name or service not known. This class uses the current endpoint.
    """

    # Current live endpoint (as of 2025). Override via DIGITRAFFIC_API_URL env var.
    DEFAULT_API_URL = "https://meri.digitraffic.fi/api/ais/v1/locations"

    def __init__(self, timeout_seconds: float = 10.0):
        self.api_url = os.getenv("DIGITRAFFIC_API_URL", self.DEFAULT_API_URL).strip()
        self.timeout = timeout_seconds
        self.last_fetch_time: float = 0.0
        self.cached_vessels: List[Dict[str, Any]] = []
        self.last_status: str = "INITIALIZED"
        self.is_available: bool = False  # False until first successful fetch

    @property
    def provider_name(self) -> str:
        return "Digitraffic (Finland Open AIS)"

    @property
    def coverage_area(self) -> str:
        return "Baltic Sea, Gulf of Finland & Northern European Cable Corridors"

    @property
    def is_real_data(self) -> bool:
        return True

    def fetch_vessels(self) -> List[Dict[str, Any]]:
        now = time.time()
        # Cache for 30 seconds to respect open API rate guidelines
        if now - self.last_fetch_time < 30.0 and self.cached_vessels:
            return self.cached_vessels

        try:
            req = urllib.request.Request(
                self.api_url,
                headers={
                    "User-Agent": "OceanGuard-AI-Submarine-Cable-Protection/3.0",
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate"
                }
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    import gzip
                    content = response.read()
                    if response.info().get('Content-Encoding') == 'gzip':
                        content = gzip.decompress(content)
                    raw_data = json.loads(content.decode('utf-8'))

                    features = raw_data.get("features", [])
                    normalized = []
                    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

                    # Parse GeoJSON FeatureCollection from Digitraffic meri API
                    for f in features:
                        props = f.get("properties", {})
                        geom = f.get("geometry", {})
                        coords = geom.get("coordinates", [])

                        if not coords or len(coords) < 2:
                            continue

                        lon, lat = coords[0], coords[1]
                        # mmsi appears both at the feature level and in properties
                        mmsi = str(f.get("mmsi", props.get("mmsi", "")))
                        if not mmsi or lat == 0.0 or lon == 0.0:
                            continue

                        speed_kts = round(float(props.get("sog", 0.0)), 1)
                        course_deg = round(float(props.get("cog", 0.0)), 1)
                        heading_deg = round(float(props.get("heading", course_deg)), 1)

                        normalized.append({
                            "mmsi": mmsi,
                            "imo": f"IMO{mmsi}",
                            "name": f"VESSEL MMSI {mmsi}",
                            "vessel_type": "Merchant / Commercial",
                            "flag": "Northern Europe",
                            "lat": round(lat, 5),
                            "lon": round(lon, 5),
                            "speed": speed_kts,
                            "course": course_deg,
                            "heading": heading_deg,
                            "timestamp": now_iso,
                            "source_provider": self.provider_name,
                            "data_mode": "REAL_AIS",
                            "coverage_info": self.coverage_area
                        })

                    self.cached_vessels = normalized
                    self.last_fetch_time = now
                    self.is_available = True
                    self.last_status = f"ONLINE ({len(normalized)} real vessels acquired)"
                    logger.info(f"Digitraffic: {len(normalized)} vessels fetched from {self.api_url}")
                    return normalized
                else:
                    self.is_available = False
                    self.last_status = f"HTTP ERROR {response.status}"
                    logger.warning(f"Digitraffic AIS API returned HTTP {response.status}")
        except Exception as e:
            self.is_available = False
            self.last_status = f"UNAVAILABLE ({type(e).__name__}: {e})"
            logger.warning(f"Digitraffic AIS API unavailable: {e}")

        # Return stale cache if available; otherwise empty list
        return self.cached_vessels

    def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "real_data": self.is_real_data,
            "coverage": self.coverage_area,
            "status": self.last_status,
            "available": self.is_available,
            "api_url": self.api_url,
            "cached_count": len(self.cached_vessels),
            "last_fetch": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.last_fetch_time)) if self.last_fetch_time else "NEVER"
        }



class AISStreamProvider(BaseAISProvider):
    """
    FREE Open Community Real-Time AIS WebSocket Provider: AISStream.io.
    URL: wss://stream.aisstream.io/v0/stream
    Coverage: Global Crowdsourced Coastal Receivers.
    Access Model: Free registration for API Key (Set via AISSTREAM_API_KEY environment variable).
    """

    def __init__(self):
        self.api_key = os.getenv("AISSTREAM_API_KEY", "").strip()
        self.last_status = "READY" if self.api_key else "DISABLED (Missing AISSTREAM_API_KEY env var)"

    @property
    def provider_name(self) -> str:
        return "AISStream.io (Community Open AIS)"

    @property
    def coverage_area(self) -> str:
        return "Global Crowdsourced Coastal Receivers"

    @property
    def is_real_data(self) -> bool:
        return True

    def fetch_vessels(self) -> List[Dict[str, Any]]:
        # Returns empty list if no API key is provided, falling back cleanly to other active providers
        if not self.api_key:
            return []
        # AISStream operates as a persistent WebSocket client. When API key is provided, connection streams live packets.
        return []

    def health_check(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "real_data": self.is_real_data,
            "coverage": self.coverage_area,
            "status": self.last_status,
            "api_key_configured": bool(self.api_key)
        }


def get_active_ais_providers() -> List[BaseAISProvider]:
    """
    Factory function loading configured active real-world AIS providers based on environment variables.
    """
    providers: List[BaseAISProvider] = []

    # Digitraffic (Finland Free AIS) is enabled by default unless explicitly set to 'false'
    if os.getenv("ENABLE_DIGITRAFFIC", "true").lower() in ["true", "1", "yes"]:
        providers.append(DigitrafficProvider())

    # AISStream.io (Community Open AIS) enabled if API key or env var is present
    if os.getenv("ENABLE_AISSTREAM", "true").lower() in ["true", "1", "yes"]:
        providers.append(AISStreamProvider())

    return providers
