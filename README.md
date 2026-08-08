# OceanGuard AI - Submarine Cable Protection AI Dashboard

OceanGuard AI is an intelligent maritime surveillance and geospatial monitoring platform engineered to safeguard critical submarine telecommunication cables against vessel strikes, anchor dragging, illegal trawling, and dark vessel intrusions.

---

## 🌟 Architecture Overview

```
                      +---------------------------------------+
                      |         GIS Map Web Dashboard         |
                      |   (Leaflet.js + Tailwind + HTML5)     |
                      +-------------------+-------------------+
                                          |
                                          v
                      +-------------------+-------------------+
                      |      FastAPI REST & WS Server         |
                      +----+-----------+-----------+----------+
                           |           |           |
            +--------------+           |           +--------------+
            v                          v                          v
+-----------------------+  +-----------------------+  +-----------------------+
|  AIS Vessel Tracker   |  | Multi-Tier Geofence   |  |   Dark Vessel SAR     |
| & Position Simulator  |  |     Engine            |  |   Detection Engine    |
+-----------------------+  +-----------------------+  +-----------------------+
            |                          |                          |
            v                          v                          v
+-----------------------+  +-----------------------+  +-----------------------+
|  Submarine Cable      |  |     AI Risk Engine    |  | Real-Time Alert Hub   |
|  GeoJSON/PostGIS DB   |  |   (0 - 100 Risk Score) |  |   (Dashboard/SMS/Mail)|
+-----------------------+  +-----------------------+  +-----------------------+
```

---

## 🚀 Key Modules Implemented

### Module 1: GIS Map Dashboard
- High-contrast cartographic dark mode basemap.
- Interactive polyline rendering of global submarine cable paths (MAREA, Grace Hopper, SEA-ME-WE 5, Trans-Pacific Express, PLCN).
- Dynamic buffer corridor overlays: **500m Critical**, **1km Monitoring**, and **5km Warning** zones.
- Real-time animated vessel movement icons with heading vectors and risk-colored highlights.

### Module 2: AIS Vessel Tracking System
- Ingests and processes vessel AIS transponder feeds (MMSI, IMO, vessel type, flag, position, speed, heading).
- Stores position trail history for trajectory mapping.
- Endpoints: `/api/vessels`, `/api/vessel/{id}`, `/api/track/history`.

### Module 3: Submarine Cable GeoJSON Database
- GeoJSON feature dataset with cable attributes: length, capacity (Tbps), landing points, depth, and protection zones.
- PostgreSQL/PostGIS compatible spatial structure.

### Module 4: Geo-Fencing Engine
- Continuous line-to-point geodesic spatial distance calculation.
- Geofence tiers:
  - **Zone 1 (5 km Warning Zone)**
  - **Zone 2 (1 km Monitoring Zone)**
  - **Zone 3 (500 m Critical Zone)**
- Dynamic threat condition triggers (Zone entry, slow speed near cables <3.5 kts, loitering >15 mins, course shifts).

### Module 5: AI Risk Engine
- Multi-factor ML scoring formula (Score 0 – 100):
  - **Distance Weight (45%)**: Proximity to cable line.
  - **Speed Weight (25%)**: Slow speeds near cable indicate anchor dragging or trawling.
  - **Vessel Type Risk (15%)**: Fishing trawlers and dredgers receive higher threat weight than cargo ships.
  - **Loitering Duration (15%)**: Cumulative minutes inside the 1km buffer.
- Risk Classification:
  - **0 – 30**: Low (Green)
  - **31 – 60**: Medium (Yellow)
  - **61 – 80**: High (Orange)
  - **81 – 100**: Critical (Red Pulsing)

### Module 6: Dark Vessel Satellite SAR Detection
- Cross-references **Sentinel-1 C-Band Synthetic Aperture Radar (SAR)** satellite imagery against active AIS broadcasts.
- Identifies unflagged vessels operating without active AIS transponders within cable protection corridors.
- Provides target RCS values, estimated length/beam, and confidence match score.

### Module 7: Alert Notification System
- Multi-channel notification pipeline (Dashboard, SMS API simulation, Email dispatch).
- Standardized alert format: Vessel Name, MMSI, Geodesic Distance, Risk Score, and Protocol Action Recommendation.

### Module 8: Security & Audit Logging
- Role-Based Access Control (RBAC): Administrator, GIS Analyst, Operator.
- Audit history logging capturing all operator actions, alert acknowledgements, and satellite sweeps.

### Module 9: Deployment & Containerization
- Dockerfile & Docker Compose configuration provided for seamless cloud deployment.

---

## 🛠️ Quick Start Guide

### Option 1: Direct Web Dashboard (Zero Installation Required)
Simply open `frontend/index.html` in any web browser to experience the full interactive GIS dashboard with built-in real-time AIS simulation, interactive threat injection, and Sentinel-1 SAR satellite pass trigger.

```bash
# Windows PowerShell
Start-Process "C:\Users\SAAD\.gemini\antigravity\scratch\OceanGuard-AI\frontend\index.html"
```

### Option 2: Running Backend API Server with FastAPI
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Open API docs at: `http://localhost:8000/docs`

### Option 3: Docker Deployment
```bash
docker-compose up -d --build
```

---

## 📡 API Reference Endpoint Table

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Root status & system module overview |
| `GET` | `/api/cables` | Submarine cable GeoJSON feature collection |
| `GET` | `/api/vessels` | Active AIS vessels with dynamic AI risk scores |
| `GET` | `/api/vessel/{mmsi}` | Single vessel metadata & position history |
| `GET` | `/api/track/history` | Track trail history for all vessels |
| `GET` | `/api/alerts` | Active geofence threat alerts |
| `POST` | `/api/alerts/acknowledge/{id}` | Mark threat alert as acknowledged |
| `GET` | `/api/dark-vessels` | Satellite SAR detected dark target list |
| `POST` | `/api/dark-vessels/scan` | Trigger Sentinel-1 SAR satellite sweep |
| `POST` | `/api/simulation/inject-suspicious` | Inject high-risk trawler demo threat |
| `POST` | `/api/simulation/toggle` | Pause or resume AIS position simulation |
| `GET` | `/api/analytics` | High-level system threat analytics |
| `GET` | `/api/audit-logs` | Security audit history log stream |

---

## 🔮 Future Improvement Roadmap

1. **Acoustic / Distributed Acoustic Sensing (DAS) Integration**: Interfacing with fiber DAS sensors along cable lines to detect physical seabed impacts in real time.
2. **Deep Learning Trajectory Prediction (LSTM / GRU)**: Predicting vessel positions 30–60 minutes in advance to issue preventative warnings before ships enter critical zones.
3. **Automated VHF Radio Voice Dispatch**: Automated synthesis of voice warnings broadcast directly to ship bridge transponders via marine VHF.
