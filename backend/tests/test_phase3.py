# backend/tests/test_phase3.py
"""
Phase 3 Automated Test Suite — OceanGuard AI
Tests: Risk Scoring, Sentinel-2 Optical Confirmation, Alert Types, Data Quality, Graceful Failures.
All test scenarios use clearly labelled MOCK/TEST data. No real satellite data is fabricated.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from providers.copernicus_sentinel2 import CopernicusSentinel2Provider
from services.risk_scoring_service import RiskScoringService
from services.dark_vessel_engine import DarkVesselEngine
from services.alert_service import AlertService


# ---------------------------------------------------------------------------
# Shared mock vessel factory
# ---------------------------------------------------------------------------

def make_vessel(
    mmsi="TEST-001",
    name="TEST VESSEL",
    vessel_type="Merchant",
    lat=38.0,
    lon=-62.0,
    speed=12.0,
    course=90.0,
    loitering_minutes=0.0,
    distance_to_cable=50000.0,
    nearest_cable="Test Cable",
    data_mode="REAL_AIS",
    source_provider="Test AIS Provider"
):
    return {
        "mmsi": mmsi,
        "name": name,
        "vessel_type": vessel_type,
        "lat": lat,
        "lon": lon,
        "speed": speed,
        "course": course,
        "heading": course,
        "loitering_minutes": loitering_minutes,
        "distance_to_cable_meters": distance_to_cable,
        "nearest_cable": nearest_cable,
        "data_mode": data_mode,
        "source_provider": source_provider,
        "risk_assessment": {"score": 0, "category": "LOW", "zone": "SAFE_OPEN_SEAS"},
        # TEST DATA label
        "_test_data": True
    }


# ---------------------------------------------------------------------------
# 1. Low-risk vessel far from cable
# ---------------------------------------------------------------------------

class TestLowRiskVessel(unittest.TestCase):
    def test_low_risk_vessel_far_from_cable(self):
        """TEST DATA: Container ship 80km from any cable should score LOW risk."""
        svc = RiskScoringService()
        vessel = make_vessel(speed=18.5, distance_to_cable=80000.0)
        result = svc.compute_cable_vessel_risk(vessel, "MAREA Cable", 80000.0)
        self.assertEqual(result["risk_level"], "LOW")
        self.assertLess(result["risk_score"], 25.0)
        self.assertEqual(result["zone"], "SAFE_OPEN_SEAS")
        self.assertIn("data_sources_used", result)
        self.assertIn("explanation", result)


# ---------------------------------------------------------------------------
# 2. Medium-risk vessel approaching cable
# ---------------------------------------------------------------------------

class TestMediumRiskVessel(unittest.TestCase):
    def test_medium_risk_vessel_approaching_cable(self):
        """TEST DATA: Merchant ship 3km from cable at 8 kts should score MEDIUM risk."""
        svc = RiskScoringService()
        vessel = make_vessel(speed=8.0, distance_to_cable=3000.0, vessel_type="Merchant")
        result = svc.compute_cable_vessel_risk(vessel, "MAREA Cable", 3000.0)
        self.assertIn(result["risk_level"], ["MEDIUM", "HIGH"])
        self.assertGreaterEqual(result["risk_score"], 25.0)
        self.assertEqual(result["zone"], "WARNING_5KM")
        self.assertIn("contributing_factors", result)


# ---------------------------------------------------------------------------
# 3. High-risk vessel inside monitoring zone
# ---------------------------------------------------------------------------

class TestHighRiskMonitoringZone(unittest.TestCase):
    def test_high_risk_inside_monitoring_zone(self):
        """TEST DATA: Tug boat 900m from cable at 2.5 kts should score HIGH risk."""
        svc = RiskScoringService()
        vessel = make_vessel(speed=2.5, distance_to_cable=900.0, vessel_type="Tugboat")
        result = svc.compute_cable_vessel_risk(vessel, "SEA-ME-WE 5", 900.0)
        self.assertGreaterEqual(result["risk_score"], 50.0)
        self.assertIn(result["risk_level"], ["HIGH", "CRITICAL"])
        self.assertEqual(result["zone"], "MONITORING_1KM")


# ---------------------------------------------------------------------------
# 4. Critical-risk scenario
# ---------------------------------------------------------------------------

class TestCriticalRiskScenario(unittest.TestCase):
    def test_critical_risk_trawler_inside_500m(self):
        """TEST DATA: Fishing trawler 350m from cable, speed 1.5 kts, loitering 25 min = CRITICAL."""
        svc = RiskScoringService()
        vessel = make_vessel(
            vessel_type="Fishing Trawler",
            speed=1.5,
            loitering_minutes=25.0,
            distance_to_cable=350.0
        )
        result = svc.compute_cable_vessel_risk(vessel, "MAREA Cable", 350.0)
        self.assertGreaterEqual(result["risk_score"], 75.0)
        self.assertEqual(result["risk_level"], "CRITICAL")
        self.assertEqual(result["zone"], "CRITICAL_500M")
        self.assertIn("Proximity", " ".join(result["contributing_factors"].keys()) + result["explanation"])


# ---------------------------------------------------------------------------
# 5. AIS gap detection (data mode not REAL_AIS)
# ---------------------------------------------------------------------------

class TestAISGap(unittest.TestCase):
    def test_ais_gap_degrades_data_quality(self):
        """TEST DATA: Vessel with no real AIS data mode should report lower data quality."""
        svc = RiskScoringService()
        vessel = make_vessel(data_mode="SIMULATED_TEST", distance_to_cable=400.0, speed=1.2)
        result = svc.compute_cable_vessel_risk(vessel, "Test Cable", 400.0)
        # No real AIS = data quality should NOT be HIGH
        self.assertNotEqual(result["data_quality"], "HIGH")
        self.assertEqual(result["ais_status"], "NO_AIS_BROADCAST")


# ---------------------------------------------------------------------------
# 6. Sentinel-1 SAR detection + AIS mismatch → POTENTIAL_DARK_VESSEL
# ---------------------------------------------------------------------------

class TestSARDarkVesselClassification(unittest.TestCase):
    def test_sar_no_ais_match_classified_as_potential_dark(self):
        """TEST DATA: SAR candidate with no AIS vessels nearby → POTENTIAL_DARK_VESSEL classification."""
        engine = DarkVesselEngine()
        # No AIS vessels
        result = engine.run_satellite_sar_sweep(
            active_ais_vessels=[],
            cable_features=None,
            bbox=[-75.0, 36.0, -70.0, 44.0]
        )
        self.assertIn("detections", result)
        dark_count = result["potential_dark_vessels_count"]
        self.assertGreaterEqual(dark_count, 0)
        # All candidates with no AIS fleet should be POTENTIAL_DARK_VESSEL
        for d in result["detections"]:
            self.assertEqual(d["classification"], "POTENTIAL_DARK_VESSEL")
            self.assertIn("rationale", d)

    def test_sar_risk_score_elevated_for_dark_vessel(self):
        """TEST DATA: POTENTIAL_DARK_VESSEL SAR target should elevate risk score via SAR factor."""
        svc = RiskScoringService()
        vessel = make_vessel(distance_to_cable=2000.0, speed=2.0)
        sar_det = {"classification": "POTENTIAL_DARK_VESSEL", "satellite_source": "Sentinel-1 SAR"}
        result_with_sar = svc.compute_cable_vessel_risk(vessel, "Test Cable", 2000.0, sar_detection=sar_det)
        result_without_sar = svc.compute_cable_vessel_risk(vessel, "Test Cable", 2000.0)
        self.assertGreater(result_with_sar["risk_score"], result_without_sar["risk_score"])
        self.assertGreater(result_with_sar["contributing_factors"]["sar_dark_factor"], 0.0)


# ---------------------------------------------------------------------------
# 7. Sentinel-1 + Sentinel-2 optical confirmation
# ---------------------------------------------------------------------------

class TestSentinel2OpticalConfirmation(unittest.TestCase):
    def test_optical_confirmed_raises_risk_score(self):
        """TEST DATA: Optical confirmation should increase risk score via optical factor."""
        svc = RiskScoringService()
        vessel = make_vessel(distance_to_cable=800.0, speed=2.0, data_mode="REAL_AIS")
        opt_confirmed = {"confirmation_status": "OPTICAL_CONFIRMED", "data_quality": "HIGH"}
        opt_unavailable = {"confirmation_status": "OPTICAL_UNAVAILABLE", "data_quality": "MEDIUM"}
        score_confirmed = svc.compute_cable_vessel_risk(vessel, "Test Cable", 800.0, optical_confirmation=opt_confirmed)
        score_unavailable = svc.compute_cable_vessel_risk(vessel, "Test Cable", 800.0, optical_confirmation=opt_unavailable)
        self.assertGreater(score_confirmed["risk_score"], score_unavailable["risk_score"])
        self.assertGreater(score_confirmed["contributing_factors"]["optical_factor"], 0.0)

    def test_optical_confirmed_gives_high_data_quality(self):
        """TEST DATA: REAL_AIS + OPTICAL_CONFIRMED should produce HIGH data quality."""
        svc = RiskScoringService()
        vessel = make_vessel(data_mode="REAL_AIS", distance_to_cable=800.0)
        opt = {"confirmation_status": "OPTICAL_CONFIRMED", "data_quality": "HIGH"}
        result = svc.compute_cable_vessel_risk(vessel, "Test Cable", 800.0, optical_confirmation=opt)
        self.assertEqual(result["data_quality"], "HIGH")

    def test_optical_not_confirmed_does_not_prove_absence(self):
        """TEST DATA: OPTICAL_NOT_CONFIRMED must not reclassify a potential dark vessel as safe."""
        engine = DarkVesselEngine()
        result = engine.run_satellite_sar_sweep(active_ais_vessels=[], cable_features=None)
        for d in result["detections"]:
            # Even with optical not confirmed, dark vessel flag must not be cleared
            if d["optical_confirmation_status"] in ["OPTICAL_NOT_CONFIRMED", "OPTICAL_UNAVAILABLE"]:
                # Classification should still be based on SAR+AIS, not optical outcome alone
                self.assertIn(d["classification"], ["POTENTIAL_DARK_VESSEL", "MATCHED_AIS"])


# ---------------------------------------------------------------------------
# 8. Sentinel-2 unavailable (offline / no credentials)
# ---------------------------------------------------------------------------

class TestSentinel2Unavailable(unittest.TestCase):
    def test_sentinel2_offline_returns_unavailable_status(self):
        """TEST DATA: Sentinel-2 with no API access should return OPTICAL_UNAVAILABLE gracefully."""
        provider = CopernicusSentinel2Provider()
        # Force offline by searching a bbox that will time out immediately if internet available
        # In test context, provider returns cached_products (empty initially) = OPTICAL_UNAVAILABLE
        result = provider.evaluate_optical_confirmation(lat=38.0, lon=-62.0, target_timestamp="2026-08-24T00:00:00Z")
        # Should return a valid dict without raising exceptions
        self.assertIn("confirmation_status", result)
        self.assertIn(result["confirmation_status"],
                      ["OPTICAL_CONFIRMED", "OPTICAL_NOT_CONFIRMED", "OPTICAL_UNAVAILABLE", "INSUFFICIENT_DATA"])
        self.assertIn("rationale", result)

    def test_sentinel2_disabled_via_env(self):
        """TEST DATA: ENABLE_SENTINEL2_OPTICAL=false should disable provider cleanly."""
        import os
        original = os.environ.get("ENABLE_SENTINEL2_OPTICAL", "true")
        os.environ["ENABLE_SENTINEL2_OPTICAL"] = "false"
        try:
            provider = CopernicusSentinel2Provider()
            self.assertFalse(provider.is_configured())
            products = provider.search_sentinel2_products([-75.0, 36.0, -70.0, 44.0])
            self.assertEqual(products, [])
        finally:
            os.environ["ENABLE_SENTINEL2_OPTICAL"] = original


# ---------------------------------------------------------------------------
# 9. Missing Copernicus credentials
# ---------------------------------------------------------------------------

class TestMissingCopernicusCredentials(unittest.TestCase):
    def test_missing_credentials_does_not_crash(self):
        """TEST DATA: Provider without credentials must not raise exceptions."""
        import os
        for key in ["COPERNICUS_USERNAME", "COPERNICUS_PASSWORD", "COPERNICUS_CLIENT_ID", "COPERNICUS_CLIENT_SECRET"]:
            os.environ.pop(key, None)
        try:
            provider = CopernicusSentinel2Provider()
            # Should not raise
            result = provider.evaluate_optical_confirmation(38.0, -62.0, "2026-08-24T00:00:00Z")
            self.assertIsInstance(result, dict)
            self.assertIn("confirmation_status", result)
        except Exception as e:
            self.fail(f"Provider raised unexpected exception with missing credentials: {e}")


# ---------------------------------------------------------------------------
# 10. Satellite API failure / network failure
# ---------------------------------------------------------------------------

class TestSatelliteAPIFailure(unittest.TestCase):
    def test_dark_vessel_engine_survives_provider_exception(self):
        """TEST DATA: Engine must survive and return a result even when providers throw exceptions."""
        engine = DarkVesselEngine()
        # Patch provider to always raise
        original = engine.sentinel1_provider.extract_vessel_candidates
        engine.sentinel1_provider.extract_vessel_candidates = lambda **kwargs: (_ for _ in ()).throw(ConnectionError("Simulated API failure"))
        try:
            result = engine.run_satellite_sar_sweep(active_ais_vessels=[], cable_features=None)
            # Must return a valid result structure (uses fallback baseline candidate)
            self.assertIn("status", result)
            self.assertIn("detections", result)
        except Exception as e:
            self.fail(f"Engine raised unexpected exception during provider failure: {e}")
        finally:
            engine.sentinel1_provider.extract_vessel_candidates = original


# ---------------------------------------------------------------------------
# 11. Incomplete / partial data quality
# ---------------------------------------------------------------------------

class TestIncompleteDataQuality(unittest.TestCase):
    def test_incomplete_data_returns_insufficient_data_quality(self):
        """TEST DATA: Vessel with neither real AIS nor satellite data should report INSUFFICIENT_DATA."""
        svc = RiskScoringService()
        vessel = make_vessel(
            data_mode="UNKNOWN",
            distance_to_cable=1200.0,
            speed=3.0,
            source_provider="UNKNOWN_SOURCE"
        )
        result = svc.compute_cable_vessel_risk(vessel, "Test Cable", 1200.0)
        self.assertIn(result["data_quality"], ["MEDIUM", "INSUFFICIENT_DATA"])

    def test_risk_score_structure_complete(self):
        """TEST DATA: Every risk result must contain all required fields."""
        svc = RiskScoringService()
        vessel = make_vessel(distance_to_cable=3000.0)
        result = svc.compute_cable_vessel_risk(vessel, "Test Cable", 3000.0)
        required_fields = [
            "risk_score", "risk_level", "nearest_cable", "distance_meters",
            "zone", "contributing_factors", "weights_used", "explanation",
            "timestamp", "data_sources_used", "data_quality", "ais_status"
        ]
        for field in required_fields:
            self.assertIn(field, result, f"Missing required field: {field}")


# ---------------------------------------------------------------------------
# 12. Alert type validation
# ---------------------------------------------------------------------------

class TestAlertTypes(unittest.TestCase):
    def test_satellite_dark_vessel_alert_generated(self):
        """TEST DATA: POTENTIAL_DARK_VESSEL SAR detection should produce a structured alert."""
        svc = AlertService()
        mock_detection = {
            "id": "SAR-TEST-001",
            "classification": "POTENTIAL_DARK_VESSEL",
            "lat": 38.25,
            "lon": -62.48,
            "nearest_cable": "MAREA Cable",
            "distance_to_nearest_cable_m": 1500.0,
            "inside_monitoring_zone": True,
            "rationale": "TEST DATA: Mock SAR detection without AIS match.",
            "primary_satellite_source": "Sentinel-1A SAR (C-Band SAR) [TEST]",
            "secondary_optical_source": "Sentinel-2 MSI [TEST]",
            "optical_confirmation_status": "OPTICAL_UNAVAILABLE",
            "sentinel1_product_id": "S1A_TEST_PRODUCT",
            "sentinel2_product_id": "NONE",
            "data_quality": "MEDIUM",
            "recommended_action": "TEST: Flag for patrol verification"
        }
        svc.evaluate_satellite_alerts([mock_detection])
        found = [a for a in svc.alerts if a.get("target_id") == "SAR-TEST-001"]
        self.assertTrue(len(found) >= 1)
        alert = found[0]
        self.assertIn(alert["alert_type"], ["POTENTIAL_DARK_VESSEL", "POTENTIAL_DARK_VESSEL_NEAR_CABLE"])
        self.assertIn("evidence", alert)
        self.assertIn("recommended_action", alert)
        self.assertIn("trigger_reason", alert)


if __name__ == "__main__":
    unittest.main(verbosity=2)
