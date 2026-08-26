# OceanGuard AI — Phase 3 Technical Documentation

## Overview

OceanGuard AI is a real-world maritime intelligence platform for submarine cable protection.
It combines AIS telemetry, Copernicus Sentinel-1 SAR radar, Sentinel-2 optical satellite imagery,
and an explainable risk-scoring engine.

---

## Free Data Sources

### 1. AIS — Automatic Identification System

| Provider | Cost | Coverage | API Key |
|---|---|---|---|
| **Digitraffic Finland** | FREE, open public API | Baltic Sea & Northern European waters | Not required |
| **AISStream.io** | FREE tier | Community global AIS feed | Required (`AISSTREAM_API_KEY`) |

**AIS Limitations:**
- AIS is a VHF radio broadcast — reception depends on proximity to shore stations or satellite AIS receivers.
- Small vessels, fishing boats < 15m gross tonnage are not legally required to carry AIS.
- AIS can be intentionally disabled or spoofed by bad actors.
- Digitraffic coverage is limited to Baltic/Northern Europe; open AIS does NOT provide worldwide real-time coverage.

### 2. Copernicus Sentinel-1 C-Band SAR (Primary Satellite Source)

| Property | Value |
|---|---|
| Cost | **FREE** — Copernicus Open Access (EU-funded) |
| Wavelength | C-Band (5.405 GHz), 5.6 cm |
| Mode | Interferometric Wide (IW) GRDH |
| Resolution | ~20m spatial |
| Polarisation | VV + VH |
| Swath Width | 250 km |
| Orbital Revisit | 6 days (single satellite); 1-3 days (Sentinel-1A + 1B combined) |
| Catalog API | https://catalogue.dataspace.copernicus.eu/ |
| Registration | Free account required for image download |

**Why Sentinel-1 is the Primary Source:**
- Operates day and night — not affected by darkness.
- Penetrates cloud cover — active radar does not depend on sunlight.
- Detects metallic vessel hulls via Radar Cross-Section (RCS) backscatter.
- Ideal for monitoring remote ocean cable corridors under all weather conditions.

### 3. Copernicus Sentinel-2 MSI Optical (Secondary Satellite Source)

| Property | Value |
|---|---|
| Cost | **FREE** — Copernicus Open Access (EU-funded) |
| Instrument | Multi-Spectral Instrument (MSI) |
| Bands | 13 spectral bands (443–2190 nm) |
| Resolution | 10m (RGB/NIR), 20m (Red-Edge/SWIR), 60m (Coastal/Cirrus) |
| Swath Width | 290 km |
| Orbital Revisit | 5 days (equator); 2-3 days (mid-latitudes with S2A+S2B) |
| Catalog API | https://catalogue.dataspace.copernicus.eu/ |
| Registration | Free account required for image download |

**Sentinel-2 Limitations:**
- **Does NOT operate at night** — passive optical sensor requires sunlight.
- **Cloud cover can completely obscure imagery** — configured threshold: 40% (env: `SENTINEL2_MAX_CLOUD_COVER`).
- Sentinel-2 is a **secondary confirmation tool only** — Sentinel-1 SAR remains the primary vessel detection source.
- `OPTICAL_NOT_CONFIRMED` does **NOT** prove a vessel is absent — cloud cover, timing gaps, or vessel movement can prevent confirmation.

---

## Architecture

```
┌─────────────────────────────────────────┐     ┌─────────────────────────────────────────┐
│     Real AIS Telemetry Providers        │     │  Copernicus Sentinel-1 SAR Hub          │
│ (Digitraffic Finland / AISStream.io)    │     │   (C-Band Radar — Primary)              │
└────────────────────┬────────────────────┘     └────────────────────┬────────────────────┘
                     │                                               │
                     ▼                                               ▼
┌─────────────────────────────────────────┐     ┌─────────────────────────────────────────┐
│  AISTrackerService                      │     │ DarkVesselEngine                        │
│ - Cable proximity enrichment            │     │ - CA-CFAR SAR Pixel Detection           │
│ - Track history buffer                  │     │ - AIS Correlation Engine                │
└────────────────────┬────────────────────┘     │ - Sentinel-2 Optical Validation         │
                     │                          └────────────────────┬────────────────────┘
                     │                                               │
                     └──────────────────────┬────────────────────────┘
                                            │
                                            ▼
                             ┌─────────────────────────────┐
                             │    RiskScoringService       │
                             │  Explainable Score 0–100    │
                             │  6 weighted factors         │
                             └──────────────┬──────────────┘
                                            │
                                            ▼
                             ┌─────────────────────────────┐
                             │    AlertService             │
                             │  7 structured alert types   │
                             └──────────────┬──────────────┘
                                            │
                                            ▼
                             ┌─────────────────────────────┐
                             │    FastAPI REST Endpoints   │
                             │ /api/vessels /api/alerts    │
                             │ /api/dark-vessels /api/risk │
                             │ /api/satellite              │
                             └─────────────────────────────┘
```

---

## Satellite Detection Methodology

### Sentinel-1 SAR Vessel Detection Algorithm (CA-CFAR)

**Algorithm:** Cell-Averaging Constant False Alarm Rate (CA-CFAR)

**Processing Pipeline:**

1. **Preprocessing & Sea/Land Clutter Estimation**
   - The lower 85% of backscatter pixel intensity values are used to estimate sea clutter distribution.
   - Sea clutter mean (μ_sea) and standard deviation (σ_sea) are computed from this distribution.
   - This discriminates bright terrestrial land returns from marine surface clutter.

2. **CFAR Adaptive Threshold**
   ```
   T_cfar = μ_sea + k × σ_sea      (default k = 4.8)
   ```
   The k factor is configurable and controls the false-alarm probability.

3. **Detection Phase**
   - All pixels with backscatter intensity > T_cfar are flagged as candidate targets.
   - Connected-component blob analysis groups adjacent bright pixels into discrete targets.

4. **Confidence & SCR Calculation**
   ```
   SCR_dB = 10 × log10(max_target_intensity / μ_sea)
   confidence = min(0.99, max(0.60, 0.50 + SCR_dB / 40.0))
   ```

5. **Georeferencing (Affine Geotransform)**
   ```
   lat = lat_max - (pixel_row / height) × (lat_max - lat_min)
   lon = lon_min + (pixel_col / width)  × (lon_max - lon_min)
   ```

6. **Vessel Length Estimation**
   ```
   estimated_length_m ≈ sqrt(cluster_pixel_count) × 20m
   ```
   Based on Sentinel-1 IW ~20m pixel resolution.

**Known Limitations:**
- Small vessels < 12m or non-metallic hulls may not produce detectable RCS backscatter.
- High sea states (waves > 4m) elevate σ_sea, increasing false alarm rate.
- Rocks, oil platforms, and sea-surface clutter can produce false positives.
- Sentinel-1 orbital revisit is 1–3 days — NOT a continuous video feed.

### Sentinel-2 Optical Confirmation Pipeline

```
Sentinel-1 vessel candidate (lat, lon, timestamp)
           ↓
Search Sentinel-2 CDSE catalog for scenes overlapping bbox
           ↓
Check cloud cover against threshold (default: 40%)
           ↓
         ┌──────────────────────────────────────┐
         │ Cloud cover ≤ threshold              │
         │   → OPTICAL_CONFIRMED / _NOT_CONF   │
         │                                      │
         │ Cloud cover > threshold OR no scene  │
         │   → OPTICAL_UNAVAILABLE              │
         └──────────────────────────────────────┘
```

**Important:** `OPTICAL_NOT_CONFIRMED` does NOT mean the vessel is absent.

---

## Explainable Risk Scoring Engine

### Score Formula

```
Risk Score = Σ (sub_score_i × weight_i)   ∈ [0, 100]
```

| Factor | Default Weight | Sub-Score Criteria |
|---|---|---|
| **Distance to cable** | 35% | 0–500m=100, 500–1000m=70–100, 1–5km=0–70, >5km=0 |
| **Speed & approach** | 20% | Stopped=100, <3.5 kts=85, <6 kts=50, transit=15 |
| **Vessel type** | 15% | Trawler/Fisher=100, Tug/Barge=70, Cable ship=15, Merchant=35 |
| **Loitering duration** | 10% | Linear 0–30 min → 0–100 (within 2km zone) |
| **Sentinel-1 SAR dark** | 10% | POTENTIAL_DARK_VESSEL=90, Any SAR=40, None=0 |
| **Sentinel-2 optical** | 10% | OPTICAL_CONFIRMED=60, NOT_CONFIRMED=30, UNAVAILABLE=0 |

### Risk Levels

| Score | Level | Color |
|---|---|---|
| 0–24 | LOW | #16A34A (Green) |
| 25–49 | MEDIUM | #EAB308 (Yellow) |
| 50–74 | HIGH | #F59E0B (Amber) |
| 75–100 | CRITICAL | #DC2626 (Red) |

All thresholds are configurable via environment variables:
`THRESH_RISK_MEDIUM`, `THRESH_RISK_HIGH`, `THRESH_RISK_CRITICAL`

---

## Dark Vessel Methodology

### Classification Tiers

| Classification | Meaning |
|---|---|
| `MATCHED_AIS` | Satellite candidate has a plausible AIS match within configured spatial/temporal tolerance |
| `NO_AIS_MATCH` | Satellite candidate found, no AIS vessel within tolerance |
| `POTENTIAL_DARK_VESSEL` | **Maximum classification** — SAR target near cable with no AIS match |
| `INSUFFICIENT_DATA` | Satellite or AIS data degraded beyond usable threshold |

### What "POTENTIAL DARK VESSEL" Means

- A radar bright target was detected by Sentinel-1 SAR.
- No matching AIS broadcast was found within configured distance/time tolerance.
- **This does NOT mean the vessel is confirmed dark, illegal, or suspicious.**
- AIS absence has multiple innocent explanations: small vessel size, VHF reception gaps, terrain masking, equipment failure.
- All such targets are flagged with a mandatory rationale string explaining the limitation.

---

## Alert Types

| Alert Type | Trigger Condition |
|---|---|
| `CABLE_APPROACH` | Vessel approaching 500m critical zone |
| `MONITORING_ZONE_INTRUSION` | Vessel inside 1km monitoring zone |
| `POTENTIAL_DARK_VESSEL` | SAR detection without AIS, away from cables |
| `POTENTIAL_DARK_VESSEL_NEAR_CABLE` | SAR detection without AIS, inside 5km cable corridor |
| `SUSPICIOUS_AIS_GAP` | Extended AIS absence for previously tracked vessel |
| `HIGH_RISK_CABLE_ACTIVITY` | Risk score ≥ 50, vessel inside 5km zone |
| `CRITICAL_CABLE_ACTIVITY` | Risk score ≥ 75, vessel inside critical zone |

---

## Data Quality Levels

| Level | Meaning |
|---|---|
| `HIGH` | Real AIS data + Sentinel-2 optical confirmation available |
| `MEDIUM` | Real AIS data OR satellite detection available, but not both |
| `LOW` | Simulated/test data or single unreliable source |
| `INSUFFICIENT_DATA` | Data too degraded or absent to draw reliable conclusions |

---

## Environment Variables

### AIS Provider Configuration

| Variable | Default | Description |
|---|---|---|
| `ENABLE_DIGITRAFFIC` | `true` | Enable Digitraffic Finland AIS provider |
| `ENABLE_AISSTREAM` | `true` | Enable AISStream.io community provider |
| `AISSTREAM_API_KEY` | *(none)* | AISStream.io API key |
| `USE_SIMULATOR_FALLBACK` | `false` | Enable dev/test simulator fleet |

### Satellite Provider Configuration

| Variable | Default | Description |
|---|---|---|
| `ENABLE_COPERNICUS_SATELLITE` | `true` | Enable Sentinel-1 SAR provider |
| `ENABLE_SENTINEL2_OPTICAL` | `true` | Enable Sentinel-2 optical provider |
| `COPERNICUS_USERNAME` | *(none)* | Copernicus CDSE account username |
| `COPERNICUS_PASSWORD` | *(none)* | Copernicus CDSE account password |
| `SENTINEL2_MAX_CLOUD_COVER` | `40.0` | Max cloud cover % for optical confirmation |
| `SAR_CORRELATION_DISTANCE_KM` | `2.0` | Spatial tolerance for AIS-SAR matching |
| `SAR_CORRELATION_TIME_MINUTES` | `30.0` | Temporal tolerance for AIS-SAR matching |

### Risk Score Configuration

| Variable | Default | Description |
|---|---|---|
| `WEIGHT_DISTANCE` | `0.35` | Cable distance factor weight |
| `WEIGHT_SPEED_COURSE` | `0.20` | Speed & approach factor weight |
| `WEIGHT_VESSEL_TYPE` | `0.15` | Vessel type risk factor weight |
| `WEIGHT_LOITERING` | `0.10` | Loitering duration factor weight |
| `WEIGHT_SAR_DARK` | `0.10` | Sentinel-1 dark vessel factor weight |
| `WEIGHT_OPTICAL_CONF` | `0.10` | Sentinel-2 optical confirmation factor weight |
| `THRESH_RISK_MEDIUM` | `25.0` | MEDIUM risk threshold |
| `THRESH_RISK_HIGH` | `50.0` | HIGH risk threshold |
| `THRESH_RISK_CRITICAL` | `75.0` | CRITICAL risk threshold |

---

## API Endpoints

### Existing (Preserved)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/vessels` | Active AIS vessel positions + risk scores |
| GET | `/api/vessel/{mmsi}` | Single vessel detail + track history |
| GET | `/api/alerts` | All active alerts (AIS + Satellite) |
| POST | `/api/alerts/acknowledge/{id}` | Acknowledge alert |
| GET | `/api/dark-vessels` | POTENTIAL DARK VESSEL list |
| POST | `/api/dark-vessels/scan` | Trigger Sentinel-1/2 satellite sweep |
| GET | `/api/cables` | Submarine cable GeoJSON |
| GET | `/api/analytics` | System analytics summary |
| GET | `/api/audit-logs` | Security audit log |
| POST | `/api/auth/login` | User authentication |
| GET | `/api/providers/status` | AIS + satellite provider health |

### New (Phase 3)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/risk` | Full fleet risk assessment with contributing factors |
| POST | `/api/risk/compute` | On-demand risk computation for MMSI or lat/lon |
| GET | `/api/satellite` | Satellite intelligence dashboard |
| GET | `/api/satellite/sentinel2` | Sentinel-2 provider status & limitations |

---

## False-Positive Limitations

1. **RCS sea clutter** — Wind-driven sea surface roughness, rain cells, and oil slicks can produce radar bright spots that mimic vessel returns.
2. **Fixed infrastructure** — Oil platforms, offshore wind turbines, and navigation buoys generate strong persistent SAR returns.
3. **AIS reception gaps** — A vessel silent on AIS does not imply illegal intent. Many legitimate vessels experience AIS outages.
4. **Temporal mismatch** — Sentinel-1 passes occur 1–3 days apart; a SAR detection and AIS timestamp may not align precisely.
5. **Cloud-obscured optical confirmation** — Cloud cover, night-time passes, and sensor saturation limit Sentinel-2 confirmation reliability.

---

*OceanGuard AI uses only free, open Copernicus satellite data and community AIS feeds.*
*No paid or proprietary data sources are used.*
*All detections are evidence-based and include mandatory rationale strings.*
