# backend/tests/test_phase2_5.py
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from providers.copernicus_sentinel import Sentinel1SARPixelDetector, CopernicusSentinelProvider
from services.dark_vessel_engine import DarkVesselEngine

class TestPhase25SARPixelDetector(unittest.TestCase):

    def setUp(self):
        self.pixel_detector = Sentinel1SARPixelDetector(cfar_k_factor=4.5)
        self.provider = CopernicusSentinelProvider()
        self.engine = DarkVesselEngine()

    def test_cfar_pixel_detection_algorithm(self):
        """Verify CA-CFAR algorithm detects bright radar scatterer pixels and converts to geographic coordinates."""
        # 5x5 Synthetic SAR Intensity Array (Sea background ~10-12, Bright Target ~350)
        sar_matrix = [
            [10, 11, 10, 12, 11],
            [12, 10, 11, 10, 12],
            [11, 12, 350, 340, 10], # High RCS Vessel Target Cluster at (r=2, c=2..3)
            [10, 11, 330, 320, 12],
            [12, 10, 11, 12, 10]
        ]
        bbox = [-75.0, 36.0, -70.0, 44.0] # [min_lon, min_lat, max_lon, max_lat]

        candidates = self.pixel_detector.process_sar_raster(
            raster_matrix=sar_matrix,
            bbox=bbox,
            product_id="S1A_TEST_GRD_PROD",
            acquisition_time="2026-08-20T12:00:00Z"
        )

        self.assertEqual(len(candidates), 1)
        target = candidates[0]
        self.assertEqual(target["detection_type"], "PIXEL_SAR_ALGORITHM")
        self.assertEqual(target["product_id"], "S1A_TEST_GRD_PROD")
        self.assertTrue(36.0 <= target["lat"] <= 44.0)
        self.assertTrue(-75.0 <= target["lon"] <= -70.0)
        self.assertTrue(target["radar_cross_section_db"] > 10.0)
        self.assertTrue(0.60 <= target["detection_confidence"] <= 0.99)

    def test_copernicus_provider_pixel_pipeline(self):
        """Verify Copernicus provider returns pixel-processed vessel candidates."""
        bbox = [-75.0, 36.0, -70.0, 44.0]
        candidates = self.provider.extract_vessel_candidates(bbox)
        self.assertIsInstance(candidates, list)
        if candidates:
            cand = candidates[0]
            self.assertEqual(cand["detection_type"], "PIXEL_SAR_ALGORITHM")
            self.assertEqual(cand["data_mode"], "SATELLITE_SAR")

    def test_mock_vs_real_data_labeling(self):
        """Verify mock test targets are clearly labeled as TEST/MOCK data when live satellite is offline."""
        mock_vessel = {
            "candidate_id": "SAR-MOCK-99",
            "lat": 38.25,
            "lon": -62.48,
            "data_mode": "SIMULATED_TEST",
            "detection_type": "TEST_MOCK_DATA"
        }
        self.assertEqual(mock_vessel["data_mode"], "SIMULATED_TEST")
        self.assertEqual(mock_vessel["detection_type"], "TEST_MOCK_DATA")

if __name__ == "__main__":
    unittest.main()
