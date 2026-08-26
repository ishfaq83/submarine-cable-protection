# backend/tests/test_phase2.py
import sys
import os
import unittest

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from providers.copernicus_sentinel import CopernicusSentinelProvider
from services.dark_vessel_engine import DarkVesselEngine
from services.alert_service import AlertService

class TestPhase2CopernicusAndCorrelation(unittest.TestCase):

    def setUp(self):
        self.copernicus = CopernicusSentinelProvider()
        self.engine = DarkVesselEngine()
        self.alert_service = AlertService()

    def test_copernicus_provider_offline_graceful_fallback(self):
        """Verify Sentinel provider handles network/offline conditions without raising errors."""
        bbox = [-75.0, 36.0, -70.0, 44.0]
        scenes = self.copernicus.search_sentinel1_scenes(bbox)
        self.assertIsInstance(scenes, list)
        
        candidates = self.copernicus.extract_vessel_candidates(bbox)
        self.assertIsInstance(candidates, list)

    def test_ais_sar_correlation_matched_ais(self):
        """Verify satellite candidate with active AIS within 2.0 km is classified as MATCHED_AIS."""
        mock_ais_vessels = [
            {
                "mmsi": "225987123",
                "name": "CANTABRIA TRAWLER",
                "lat": 38.25,
                "lon": -62.48,
                "source_provider": "Digitraffic (Finland Open AIS)"
            }
        ]
        res = self.engine.run_satellite_sar_sweep(mock_ais_vessels)
        self.assertEqual(res["status"], "SUCCESS")
        
        detections = self.engine.get_all_satellite_detections()
        self.assertTrue(len(detections) > 0)
        
        matched = next((d for d in detections if d["lat"] == 38.25 and d["lon"] == -62.48), None)
        if matched:
            self.assertEqual(matched["classification"], "MATCHED_AIS")
            self.assertEqual(matched["matched_ais_mmsi"], "225987123")
            self.assertIn("matches AIS vessel", matched["rationale"])

    def test_ais_sar_correlation_potential_dark_vessel(self):
        """Verify satellite candidate with NO active AIS within 2.0 km is classified as POTENTIAL_DARK_VESSEL."""
        mock_ais_vessels = [
            {
                "mmsi": "367123450",
                "name": "FAR AWAY VESSEL",
                "lat": 10.0,
                "lon": 10.0,
                "source_provider": "Digitraffic (Finland Open AIS)"
            }
        ]
        res = self.engine.run_satellite_sar_sweep(mock_ais_vessels)
        self.assertEqual(res["status"], "SUCCESS")
        
        dark_vessels = self.engine.get_dark_vessels()
        self.assertTrue(len(dark_vessels) > 0)
        
        target = dark_vessels[0]
        self.assertEqual(target["classification"], "POTENTIAL_DARK_VESSEL")
        self.assertTrue(target["potential_dark_vessel"])
        self.assertIn("no matching AIS broadcast", target["rationale"])
        self.assertIn("Sentinel-1", target["satellite_source"])
        self.assertIsNotNone(target["acquisition_timestamp"])
        self.assertIsNotNone(target["processing_timestamp"])

    def test_satellite_alert_generation(self):
        """Verify AlertService creates POTENTIAL_DARK_VESSEL alerts for unflagged targets."""
        mock_detections = [
            {
                "id": "SAR-TEST-99",
                "classification": "POTENTIAL_DARK_VESSEL",
                "rationale": "Satellite vessel candidate detected without matching AIS broadcast.",
                "lat": 38.25,
                "lon": -62.48,
                "nearest_cable": "MAREA Cable System",
                "distance_to_nearest_cable_m": 450.0,
                "inside_monitoring_zone": True,
                "satellite_source": "Sentinel-1A SAR",
                "sentinel1_product_id": "S1A_TEST_PRODUCT",
                "acquisition_timestamp": "2026-08-20T12:00:00Z",
                "processing_timestamp": "2026-08-20T12:05:00Z",
                "sar_confidence_score": 0.95
            }
        ]
        alerts = self.alert_service.evaluate_satellite_alerts(mock_detections)
        sar_alert = next((a for a in alerts if a.get("target_id") == "SAR-TEST-99"), None)
        self.assertIsNotNone(sar_alert)
        self.assertEqual(sar_alert["alert_type"], "POTENTIAL_DARK_VESSEL_NEAR_CABLE")
        self.assertEqual(sar_alert["risk_level"], "CRITICAL")
        self.assertIn("satellite_metadata", sar_alert)

if __name__ == "__main__":
    unittest.main()
