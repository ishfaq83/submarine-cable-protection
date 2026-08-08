# Generate MS Word User Guide for OceanGuard AI
Add-Type -AssemblyName System.Drawing

$docPath = "C:\Users\SAAD\.gemini\antigravity\scratch\OceanGuard-AI\OceanGuard_AI_User_Guide.docx"


Write-Host "Initializing Microsoft Word COM Object..."
$word = New-Object -ComObject Word.Application
$word.Visible = $false

$doc = $word.Documents.Add()
$selection = $word.Selection

function Add-DocTitle ($text) {
    $selection.Style = "Title"
    $selection.Font.Name = "Segoe UI"
    $selection.Font.Size = 24
    $selection.Font.Bold = 1
    $selection.Font.Color = [System.Drawing.ColorTranslator]::ToOle([System.Drawing.Color]::FromArgb(10, 30, 60))
    $selection.ParagraphFormat.SpaceAfter = 12
    $selection.TypeText($text)
    $selection.TypeParagraph()
}

function Add-DocSubtitle ($text) {
    $selection.Style = "Subtitle"
    $selection.Font.Name = "Segoe UI"
    $selection.Font.Size = 13
    $selection.Font.Italic = 1
    $selection.Font.Color = [System.Drawing.ColorTranslator]::ToOle([System.Drawing.Color]::FromArgb(0, 120, 180))
    $selection.ParagraphFormat.SpaceAfter = 18
    $selection.TypeText($text)
    $selection.TypeParagraph()
}

function Add-Heading1 ($text) {
    $selection.Style = "Heading 1"
    $selection.Font.Name = "Segoe UI"
    $selection.Font.Size = 16
    $selection.Font.Bold = 1
    $selection.Font.Color = [System.Drawing.ColorTranslator]::ToOle([System.Drawing.Color]::FromArgb(15, 45, 90))
    $selection.ParagraphFormat.SpaceBefore = 14
    $selection.ParagraphFormat.SpaceAfter = 8
    $selection.TypeText($text)
    $selection.TypeParagraph()
}

function Add-Heading2 ($text) {
    $selection.Style = "Heading 2"
    $selection.Font.Name = "Segoe UI"
    $selection.Font.Size = 13
    $selection.Font.Bold = 1
    $selection.Font.Color = [System.Drawing.ColorTranslator]::ToOle([System.Drawing.Color]::FromArgb(0, 100, 160))
    $selection.ParagraphFormat.SpaceBefore = 10
    $selection.ParagraphFormat.SpaceAfter = 6
    $selection.TypeText($text)
    $selection.TypeParagraph()
}

function Add-Paragraph ($text) {
    $selection.Style = "Normal"
    $selection.Font.Name = "Calibri"
    $selection.Font.Size = 11
    $selection.Font.Color = [System.Drawing.ColorTranslator]::ToOle([System.Drawing.Color]::FromArgb(40, 40, 40))
    $selection.ParagraphFormat.SpaceAfter = 6
    $selection.ParagraphFormat.LineSpacing = 1.15
    $selection.TypeText($text)
    $selection.TypeParagraph()
}

function Add-Callout ($title, $text) {
    $selection.ParagraphFormat.LeftIndent = 18
    $selection.ParagraphFormat.RightIndent = 18
    $selection.ParagraphFormat.SpaceBefore = 8
    $selection.ParagraphFormat.SpaceAfter = 8
    $selection.Font.Name = "Calibri"
    $selection.Font.Size = 10.5
    $selection.Font.Bold = 1
    $selection.Font.Color = [System.Drawing.ColorTranslator]::ToOle([System.Drawing.Color]::FromArgb(180, 40, 40))
    $selection.TypeText("[$title] ")
    $selection.Font.Bold = 0
    $selection.Font.Color = [System.Drawing.ColorTranslator]::ToOle([System.Drawing.Color]::FromArgb(60, 60, 60))
    $selection.TypeText($text)
    $selection.TypeParagraph()
    $selection.ParagraphFormat.LeftIndent = 0
    $selection.ParagraphFormat.RightIndent = 0
}

function Add-Bullet ($text) {
    $selection.Style = "Normal"
    $selection.Font.Name = "Calibri"
    $selection.Font.Size = 11
    $selection.ParagraphFormat.LeftIndent = 18
    $selection.ParagraphFormat.SpaceAfter = 3
    $selection.TypeText("- " + $text)
    $selection.TypeParagraph()
    $selection.ParagraphFormat.LeftIndent = 0
}

# --- DOCUMENT CONTENT GENERATION ---

Write-Host "Building Document Content..."

# Document Header Title
Add-DocTitle "OceanGuard AI -- Submarine Cable Protection Dashboard"
Add-DocSubtitle "Comprehensive System Architecture, Operations & Operator User Guide (Version 1.0 Sentinel)"

Add-Paragraph "Document Reference: MSOC-SOP-2026-004 | Target Audience: Maritime Operations Engineers, GIS Analysts, Coast Guard Command Centers, System Administrators"

# 1. Executive Summary
Add-Heading1 "1. Executive Summary & Operational Mission"
Add-Paragraph "Submarine telecommunication cables form the backbone of global digital infrastructure, carrying over 99% of international data traffic. However, these critical undersea cables are increasingly vulnerable to commercial seabed anchoring, illegal bottom trawling, dredging, and covert dark vessel threats."
Add-Paragraph "OceanGuard AI is an enterprise maritime surveillance and geospatial AI platform built to detect, analyze, and mitigate threats to submarine cable infrastructure in real time. The platform fuses automatic identification system (AIS) transponder tracking, multi-tier spatial geofencing, multi-factor AI risk evaluation, and Synthetic Aperture Radar (SAR) satellite dark vessel cross-referencing into a unified Web GIS command interface."

# 2. System Architecture
Add-Heading1 "2. System Architecture Overview"
Add-Paragraph "OceanGuard AI operates on a modular, decoupled full-stack architecture designed for real-time responsiveness and high spatial precision."

Add-Heading2 "Technology Stack Specification"
Add-Bullet "Frontend Interface: React.js, TypeScript, Leaflet.js Interactive Web GIS, Tailwind CSS, Lucide Icons."
Add-Bullet "Backend API Services: Python FastAPI with Uvicorn async execution engine."
Add-Bullet "Spatial Database: PostgreSQL 15 with PostGIS 3.3 geospatial extension supporting GeoJSON & Shapefile layers."
Add-Bullet "AIS Processing Engine: Dynamic position predictor, vector heading solver, and historical trail logger."
Add-Bullet "AI Risk Engine: Multi-variable risk evaluator calculating scores between 0.0 and 100.0."
Add-Bullet "Dark Vessel Engine: Sentinel-1 C-Band SAR satellite radar return matching algorithm."
Add-Bullet "Deployment: Docker containerization with Docker Compose orchestration."

# 3. Comprehensive Module Breakdown
Add-Heading1 "3. Comprehensive Module Operations Guide"

Add-Heading2 "Module 1: GIS Map Dashboard"
Add-Paragraph "The GIS Map Dashboard provides operators with an intuitive dark-themed global maritime picture. Key features include:"
Add-Bullet "High-Contrast Cartography: CartoDB DarkMatter basemap optimized for continuous operational monitoring."
Add-Bullet "Cable Polyline Layers: Highlighting global fiber routes including MAREA, Grace Hopper, SEA-ME-WE 5, Trans-Pacific Express (TPE), and Pacific Light (PLCN)."
Add-Bullet "Visual Buffer Corridors: Toggleable spatial buffers demarcating 500m Critical (Red), 1km Monitoring (Orange), and 5km Warning (Yellow) corridors."
Add-Bullet "Animated Vessel Markers: Vessel icons rotated dynamically along their reported heading vector, color-coded by AI threat level."

Add-Heading2 "Module 2: AIS Vessel Tracking Engine"
Add-Paragraph "The AIS Tracking Engine continuously receives and logs ship transponder broadcasts. Tracked parameters include MMSI, IMO Number, Vessel Name, Flag, Vessel Type, Latitude/Longitude, Speed Over Ground (kts), Heading (degrees), and Course Over Ground (degrees)."
Add-Paragraph "Historical position trails up to 50 past coordinates are maintained to project vessel trajectory vectors."

Add-Heading2 "Module 3: Submarine Cable GIS Database"
Add-Paragraph "Submarine cable routes are stored as high-precision LineString geometries in GeoJSON and PostGIS formats. Each cable feature contains operational metadata including length (km), fiber capacity (Tbps), landing station locations, average depth (m), and defined protection buffer radiuses."

Add-Heading2 "Module 4: Spatial Geo-Fencing Engine"
Add-Paragraph "The spatial engine evaluates geodesic line-to-point distances using the Haversine formula and equirectangular projection to determine the exact distance between any ship and the nearest submarine cable segment. The engine enforces three strict security zones:"
Add-Bullet "Zone 1 -- 5 km Warning Zone: Early awareness buffer for incoming vessels."
Add-Bullet "Zone 2 -- 1 km Monitoring Zone: Active tracking buffer. Heightened scrutiny applied to speed and heading changes."
Add-Bullet "Zone 3 -- 500 meter Critical Zone: High-hazard zone. Any vessel operating inside this zone at slow speed (<3.5 kts) triggers immediate critical alerts."

Add-Heading2 "Module 5: AI Risk Engine"
Add-Paragraph "The AI Risk Engine processes multi-factor maritime telemetry to calculate a real-time Risk Score ranging from 0.0 (Safe) to 100.0 (Critical Threat)."
Add-Paragraph "Mathematical Scoring Formula Breakdown:"
Add-Bullet "Distance Factor (Max 45 pts): Exponential threat penalty for vessels approaching within 1000m and 500m of a cable."
Add-Bullet "Speed Anomaly (Max 25 pts): Vessels moving below 3.5 knots near cable lines indicate potential seabed anchoring or trawling."
Add-Bullet "Vessel Type Factor (Max 15 pts): Higher baseline risk assigned to fishing trawlers, dredgers, and tugs compared to container vessels."
Add-Bullet "Loitering Duration (Max 15 pts): Cumulative time spent inside the 1km protection zone."

Add-Callout "RISK LEVEL CLASSIFICATION", "0-30: LOW (Green) | 31-60: MEDIUM (Yellow) | 61-80: HIGH (Orange) | 81-100: CRITICAL (Red Pulsing Alert)"

Add-Heading2 "Module 6: Dark Vessel Satellite SAR Detection"
Add-Paragraph "Vessels engaging in malicious seabed activity often disable their AIS transponders to evade tracking. OceanGuard AI integrates Synthetic Aperture Radar (SAR) imagery from Sentinel-1 satellites (C-Band radar operating in VV and VH polarisations)."
Add-Paragraph "The engine cross-references radar reflections against active AIS broadcasts within a 2km radius. If a metallic radar return is detected on satellite imagery with NO matching AIS broadcast, it is flagged as a 'Dark Vessel' with an estimated length/beam profile, Radar Cross Section (RCS in dB), and confidence score."

Add-Heading2 "Module 7: Real-Time Alert Notification System"
Add-Paragraph "When threat criteria are met, the Alert System automatically formats and dispatches notification packages across three channels: Dashboard Popups, Email Notifications, and SMS API Integration."
Add-Paragraph "Alert Payload Format: Vessel Name & MMSI | Location (Lat/Lon) | Distance from Cable (meters) | Risk Category & Score | Protocol Action Recommendation."

Add-Heading2 "Module 8: Security & Audit Logging"
Add-Paragraph "Role-Based Access Control (RBAC) restricts system capabilities across three tiers: Administrator, GIS Analyst, and Operator. All critical events--including alert acknowledgements, threat demo injections, and satellite sweeps--are recorded in an immutable audit trail."

Add-Heading2 "Module 9: Containerized Deployment"
Add-Paragraph "OceanGuard AI is fully containerized using Docker and Docker Compose, enabling deployment on cloud infrastructure (AWS EC2, Azure VM, GCP Compute Engine) or local command center servers."

# 4. Standard Operating Procedures
Add-Heading1 "4. Standard Operating Procedures for Operators"

Add-Heading2 "Procedure 1: Responding to a 500m Critical Alert"
Add-Bullet "Step 1: Click on the flashing red alert card in the Live Alerts Feed sidebar."
Add-Bullet "Step 2: The GIS map automatically pans and zooms to the target vessel, displaying its 500m proximity corridor."
Add-Bullet "Step 3: Click 'Inspect AI Risk Radar' to open the Vessel Detail Modal and analyze speed, distance breakdown, and loitering time."
Add-Bullet "Step 4: Issue a direct VHF Channel 16 radio broadcast to the vessel warning against anchor deployment."
Add-Bullet "Step 5: Click 'Acknowledge & Notify Coast Guard' to record operator response in the audit log."

Add-Heading2 "Procedure 2: Triggering a Sentinel-1 Satellite SAR Scan"
Add-Bullet "Step 1: Click the 'SAR Satellite Sweep' button in the top navigation bar."
Add-Bullet "Step 2: The system initiates a simulated Sentinel-1 orbital pass over active cable lines."
Add-Bullet "Step 3: Switch to the 'Dark SAR' tab in the sidebar to review detected unflagged radar targets."

# 5. API Quick Reference
Add-Heading1 "5. API Quick Reference Endpoint Table"
Add-Paragraph "The FastAPI backend exposes the following REST endpoints for integration with external naval command systems:"
Add-Bullet "GET /api/cables -- Returns GeoJSON feature collection of all monitored cable lines."
Add-Bullet "GET /api/vessels -- Returns active AIS vessels with spatial distance and AI risk scores."
Add-Bullet "GET /api/vessel/{mmsi} -- Returns specific vessel metadata and position track history."
Add-Bullet "GET /api/alerts -- Returns live and historical geofence threat alerts."
Add-Bullet "POST /api/alerts/acknowledge/{id} -- Acknowledges an active threat alert."
Add-Bullet "GET /api/dark-vessels -- Returns satellite SAR detected dark target list."
Add-Bullet "POST /api/dark-vessels/scan -- Triggers a fresh Sentinel-1 SAR orbital sweep."
Add-Bullet "POST /api/simulation/inject-suspicious -- Injects a high-risk threat demo vessel."

# 6. Conclusion
Add-Heading1 "6. Future Roadmap"
Add-Paragraph "Future iterations of OceanGuard AI will incorporate Distributed Acoustic Sensing (DAS) fiber optic acoustic monitoring, LSTM deep learning trajectory prediction (30-60 minute forward projection), and direct integration with commercial optical satellite constellations (Planet Labs / Maxar) for high-resolution visual confirmation."

# Save Document
$doc.SaveAs([ref]$docPath)
$doc.Close()
$word.Quit()

Write-Host "OceanGuard AI User Guide MS Word document successfully created at: $docPath"
