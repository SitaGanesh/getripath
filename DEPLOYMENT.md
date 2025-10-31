## DEPLOYMENT & MAINTENANCE GUIDE

This repository contains a Flask backend and a simple frontend for calculating optimal routes using OpenStreetMap-based services (Photon for autocomplete, Nominatim for fallback geocoding) and OSRM for routing. This document consolidates deployment instructions, troubleshooting notes, and recent fixes related to geocoding/routing.

If you previously used Google APIs, note that the project now defaults to OSM services. Google API keys remain optional and can be provided via environment variables.

---

## Quick summary
- Backend: Flask (app.py)
- Frontend: index.html, script.js, style.css (Leaflet for maps)
- Default external services: Photon (autocomplete), Nominatim (fallback geocode), OSRM (routing)
- Config via environment variables (see below)

---

## Environment variables
Set these in your hosting environment (or in a local `.env` during development). Do NOT commit `.env` to the repository.

- PHOTON_URL (default: https://photon.komoot.io/api)
- NOMINATIM_SEARCH_URL (default: https://nominatim.openstreetmap.org/search)
- OSRM_BASE_URL (default: https://router.project-osrm.org)
- BACKEND_URL (optional; tests/readers may use this)
- GOOGLE_API_KEY (optional)
- GOOGLE_DISTANCE_MATRIX_URL (optional)

For local development the repository includes `.env.example` — copy it to `.env` and edit values.

---

## Run locally (quick)

1. Install dependencies:

   pip install -r requirements.txt

2. (Optional) Copy `.env.example` to `.env` and fill values.

3. Start the backend:

   python app.py

4. Open `index.html` in your browser (or use the included `run.bat` / `start.bat` scripts).

5. Test health endpoint:

   curl http://localhost:5000/health

---

## Deploying to Render (recommended quick guide)

1. Create a `Procfile` with:

   web: gunicorn app:app --bind 0.0.0.0:$PORT

2. In Render dashboard set the environment variables listed above.

3. Build command: `pip install -r requirements.txt`

4. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT` (if you don't use the Procfile).

Notes:
- Use Render's Environment settings to keep API keys secret.
- If you host your own OSRM or Photon instances, point the corresponding env vars to those endpoints.

---

## Tests & verification

- Unit tests live in `tests/` and can be run with `python -m unittest`.
- Integration tests and dev helpers are in `dev/` and top-level test files. They load dotenv values by design.
- `test_backend.py` exercises `/health`, `/` and basic route endpoints; ensure `BACKEND_URL` is set for remote testing.

---

## Recent fixes & troubleshooting (important)

Root cause summary (why some runs returned sentinel 999999 values):
- The main cause was Nominatim rate limiting (HTTP 403) when many geocode requests were issued quickly.
- When geocoding failed, some OSRM calls lacked coordinates and the app previously returned sentinel 999999 distances.

What we changed:
- Photon-first autocomplete: Photon is queried for suggestions first (less restrictive), Nominatim used as a fallback for missing/noisy queries.
- Persistent geocode cache: `geocode_cache.json` stores normalized queries -> coordinates to avoid repeating geocoding requests.
- Nominatim politeness:
  - Delay increased from 1.0s to 2.0s between requests.
  - Retries reduced and backoff increased.
  - On 403 responses the server pauses briefly before retrying to avoid immediate re-blocking.
- OSRM usage:
  - Use OSRM `/table` endpoint to build distance matrix in one call when possible.
  - For missing table entries, fall back to pairwise `/route` requests to fill gaps.

Quick recovery steps if you hit rate limiting:
1. Wait 5–10 minutes before retrying (Nominatim temporary block).
2. Use the cache: manually add frequent locations to `geocode_cache.json` if needed.
3. Consider running your own Nominatim or using a commercial geocoding provider for heavy workloads.

Example cache entries you can add to `geocode_cache.json`:

```
{
  "mumbai": [19.0760, 72.8777],
  "goa": [15.3004543, 74.0855134]
}
```

---

## Troubleshooting & common issues

- Port in use: `netstat -ano | findstr :5000` then `taskkill /PID <PID> /F`.
- Missing Python modules: `pip install -r requirements.txt`.
- Cannot connect to backend: ensure `app.py` is running and check `curl http://localhost:5000/health`.
- CORS issues: ensure Flask-CORS is installed and backend is restarted after config changes.

If you see many `Read timed out` or `403` errors while running integration tests, it's usually network/service rate limiting.

---

## Security checklist (production)

- Move API keys into environment variables
- Restrict API keys where possible
- Serve via HTTPS (reverse proxy or platform-managed)
- Add authentication if you expose the service publicly
- Set up monitoring and logging

---

## File layout (important files)

DistanceOptimalityProblem/
- app.py            # Flask backend and TSP solver
- index.html        # Frontend UI
- script.js         # Frontend logic (calls backend endpoints, renders Leaflet map)
- style.css         # Styling
- geocode_cache.json # Persistent geocode cache (auto-updated)
- requirements.txt  # Python deps (includes python-dotenv)
- tests/            # Unit tests
- dev/              # Development helpers

---

## Next steps & recommendations

- If you plan heavy geocoding, run your own Nominatim or pay for a commercial geocoding API.
- Add a CI workflow to run unit tests on PRs (optional — I can add this).
- Keep the geocode cache under version control only if you understand the privacy implications; otherwise keep it generated at runtime.

---

If you'd like, I can now remove `DEPLOY.md` and `FIXES.md`, or move them into `dev/docs/` as backups. Tell me which you prefer and I'll proceed.

---

Last verified: the backend exposes `/health` and the geocoding/routing fixes are implemented. Unit tests and backend tests were run during the previous session.
# 🚀 COMPLETE DEPLOYMENT GUIDE

## Production-Ready TSP Distance Optimizer

This guide provides everything you need to run the application in production.

---

## 📦 What You Need to Run

### 1. **Backend (Python Flask Server)**
   - **Required:** Python 3.8+
   - **Dependencies:** Flask, Flask-CORS, requests
   - **Port:** 5000
   - **Status:** ✅ Running (if you see backend window)

### 2. **Frontend (HTML/CSS/JavaScript)**
   - **Required:** Modern web browser (Chrome, Firefox, Edge, Safari)
   - **Files:** index.html, script.js, style.css
   - **Dependencies:** OpenStreetMap-based services (Photon/Nominatim) and OSRM (default). Google APIs are optional.
   - **Status:** Opens automatically

### 3. **External Services**
   - **OSRM** - For routing and distance calculations (table/route APIs)
   - **Photon (Komoot)** - Preferred for autocomplete and geocoding
   - **Nominatim (OpenStreetMap)** - Fallback geocoding
   - **Status:** ✅ OSM-based services are the default; Google APIs are optional and can be configured via environment variables

---

## 🎯 QUICK START (Choose One Method)

### Method 1: ONE-CLICK START (Recommended)

**Double-click:** `run.bat`

This will:
1. ✅ Check if backend is running
2. ✅ Start backend in new window
3. ✅ Wait for server initialization
4. ✅ Open frontend in your browser
5. ✅ Display status information

### Method 2: MANUAL START

**Step 1:** Start backend
```powershell
python app.py
```

**Step 2:** Open frontend
- Double-click `index.html`, or
- Drag `index.html` to your browser

### Method 3: SETUP + START

**First time only:**
```powershell
setup.bat
```

**Then start:**
```powershell
start.bat
```

---

## 📋 MANUAL COMMANDS (If You Prefer Terminal)

### Install Dependencies
```powershell
# Navigate to project folder
cd D:\DistanceOptimalityProblem

# Install all dependencies
pip install -r requirements.txt

# Or install individually
pip install Flask Flask-CORS requests
```

### Start Backend Server
```powershell
# Start Flask server
python app.py

# You should see:
# ============================================================
# TSP Distance Optimizer Backend Server
# ============================================================
# Server starting on http://localhost:5000
```

### Verify Backend is Running
```powershell
# Test health endpoint
curl http://localhost:5000/health

# Expected response: {"status":"healthy"}
```

### Open Frontend
```powershell
# Open in default browser
start index.html

# Or specify browser
start chrome index.html
start firefox index.html
start msedge index.html
```

### Test Connection
```powershell
# Open test page
start test.html

# This will auto-check backend connection
```

### Stop Server
```powershell
# Method 1: Press Ctrl+C in backend terminal

# Method 2: Run stop script
stop.bat

# Method 3: Kill Python processes
taskkill /F /IM python.exe
```

---

## 🧪 TESTING & VERIFICATION

### Test Backend Connection

**Option 1: Use Test Page**
```powershell
start test.html
```
Click "Check Backend Health" button

**Option 2: Use Browser**
Open: `http://localhost:5000`

**Option 3: Use curl**
```powershell
curl http://localhost:5000/health
```

### Run Automated Tests
```powershell
python test_backend.py
```

This will test:
- ✅ Health endpoint
- ✅ Home endpoint
- ✅ Basic route calculation (2 locations)
- ✅ Complex route calculation (5 locations)
- ✅ Error handling

---

## 🏗️ PRODUCTION DEPLOYMENT

### For Local Network Access

**Current setup allows network access:**
- Your computer: `http://localhost:5000`
- Other devices: `http://YOUR_IP:5000` (e.g., `http://192.168.43.114:5000`)

**To find your IP:**
```powershell
ipconfig | findstr IPv4
```

**Access from phone/tablet:**
1. Connect to same WiFi network
2. Open browser
3. Navigate to `http://YOUR_IP:5000`
4. Open `index.html` from that URL

### For Internet Deployment

**Option 1: Use ngrok (Quick tunnel)**
```powershell
# Download ngrok from: https://ngrok.com/download

# Run ngrok
ngrok http 5000

# You'll get a public URL like: https://abc123.ngrok.io
# Share this URL with others
```

**Option 2: Deploy to Cloud**

**Heroku:**
```powershell
# Install Heroku CLI
# Create Procfile:
web: python app.py

# Deploy:
heroku create your-app-name
git push heroku main
```

**PythonAnywhere:**
1. Upload files to PythonAnywhere
2. Create web app with Flask
3. Configure WSGI file
4. Set to always running

**AWS / Azure / Google Cloud:**
- Use EC2 / App Service / Compute Engine
- Install Python and dependencies
- Open port 5000
- Run application

---

## 🔧 CONFIGURATION

### Change Port

**In `app.py` (last line):**
```python
app.run(debug=True, host='0.0.0.0', port=8080)  # Change 5000 to 8080
```

**In `script.js` (line ~231):**
```javascript
const response = await fetch('http://localhost:8080/calculate-route', {
```

### Change API Key

**Backend - `app.py` (line 12):**
```python
GOOGLE_API_KEY = 'YOUR_NEW_API_KEY'
```

**Frontend - `script.js` (line 4):**
```javascript
const API_KEY = 'YOUR_NEW_API_KEY';
```

**Frontend - `index.html` (line 48):**
```html
<script src="https://maps.googleapis.com/maps/api/js?key=YOUR_NEW_API_KEY&libraries=places&callback=initMap"></script>
```

### Enable HTTPS (Production)

**Use a reverse proxy (nginx/Apache):**
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📊 MONITORING & LOGS

### Check Backend Logs

Logs are displayed in the backend terminal window:
- Request logs
- Error messages
- Distance calculations
- Route computations

### Backend Endpoints for Monitoring

**Health Check:**
```
GET http://localhost:5000/health
Response: {"status": "healthy"}
```

**API Information:**
```
GET http://localhost:5000/
Response: {API version, endpoints, etc.}
```

### Performance Metrics

| Locations | API Calls | Time (approx) |
|-----------|-----------|---------------|
| 2         | 1         | 2-5 seconds   |
| 5         | 1         | 5-10 seconds  |
| 10        | 1         | 10-20 seconds |
| 25        | 1         | 20-40 seconds |

---

## 🛠️ TROUBLESHOOTING

### Issue: "Port 5000 already in use"

**Solution 1: Kill existing process**
```powershell
netstat -ano | findstr :5000
taskkill /PID <PID_NUMBER> /F
```

**Solution 2: Change port**
Edit `app.py` and change port to 8080 or any available port

### Issue: "Module not found: flask"

**Solution:**
```powershell
pip install Flask Flask-CORS requests
```

### Issue: "Cannot connect to backend"

**Check 1: Is backend running?**
```powershell
curl http://localhost:5000/health
```

**Check 2: Firewall blocking?**
- Allow Python through Windows Firewall
- Allow port 5000

**Check 3: CORS error?**
- Make sure Flask-CORS is installed
- Restart backend server

### Issue: "API key error"

**Solution:**
1. Go to Google Cloud Console
2. Enable required APIs:
   - Distance Matrix API
   - Places API
   - Maps JavaScript API
   - Geocoding API
3. Check billing is enabled
4. Verify API key restrictions

### Issue: "No autocomplete suggestions"

**Solution:**
- Check internet connection
- Verify Google Places API is enabled
- Clear browser cache
- Check browser console for errors (F12)

---

## 📁 FILE STRUCTURE

```
DistanceOptimalityProblem/
│
├── 🚀 Quick Start Scripts
│   ├── run.bat              # Complete start (backend + frontend)
│   ├── start.bat            # Start application
│   ├── setup.bat            # First-time setup
│   └── stop.bat             # Stop all servers
│
├── 🌐 Frontend Files
│   ├── index.html           # Main application UI
│   ├── script.js            # JavaScript logic
│   ├── style.css            # Styles and design
│   └── test.html            # Connection test page
│
├── 🐍 Backend Files
│   ├── app.py               # Flask server
│   ├── requirements.txt     # Python dependencies
│   └── test_backend.py      # Backend tests
│
└── 📖 Documentation
    ├── README.md            # Complete documentation
    ├── QUICKSTART.md        # Quick start guide
    └── DEPLOYMENT.md        # This file
```

---

## 🔐 SECURITY CHECKLIST

For production deployment:

- [ ] Move API keys to environment variables
- [ ] Enable API key restrictions in Google Cloud Console
- [ ] Set up HTTPS/SSL
- [ ] Add rate limiting
- [ ] Implement authentication (if needed)
- [ ] Enable CORS only for specific domains
- [ ] Set up monitoring and alerts
- [ ] Regular security updates
- [ ] Backup important data
- [ ] Configure proper error handling

---

## 💡 USAGE EXAMPLES

### Example 1: Plan Road Trip
```
Locations:
1. Mumbai, Maharashtra
2. Goa
3. Bangalore, Karnataka
4. Hyderabad, Telangana

Result: Optimal route with total distance
```

### Example 2: Delivery Route
```
Locations:
1. Warehouse, Pune
2. Customer A, Hadapsar
3. Customer B, Kothrud
4. Customer C, Hinjewadi

Result: Most efficient delivery route
```

### Example 3: Tourist Spots
```
Locations:
1. Charminar, Hyderabad
2. Golconda Fort
3. Hussain Sagar
4. Ramoji Film City

Result: Optimized sightseeing route
```

---

## 📞 SUPPORT & HELP

### Check Status
```powershell
# Backend status
curl http://localhost:5000/health

# System info
python --version
pip list | findstr "Flask"
```

### Get Logs
- Backend logs: Check backend terminal window
- Browser logs: Press F12 → Console tab

### Common Commands Reference

```powershell
# Start everything
run.bat

# Just backend
python app.py

# Just frontend
start index.html

# Test connection
start test.html

# Stop everything
stop.bat

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## ✅ PRE-FLIGHT CHECKLIST

Before starting the application:

1. [ ] Python 3.8+ installed
2. [ ] pip working
3. [ ] All dependencies installed (`pip install -r requirements.txt`)
4. [ ] Port 5000 available
5. [ ] Internet connection active (for Photon/OSRM or your configured services)
6. [ ] Optional: Google API key configured if you intend to use Google services
7. [ ] Required APIs enabled in Google Cloud Console

---

## 🎉 YOU'RE READY!

### To Start Application NOW:

**Option 1 (Easiest):**
```powershell
run.bat
```

**Option 2 (Manual):**
```powershell
# Terminal 1 (Backend)
python app.py

# Then open index.html in browser
```

**Option 3 (Test First):**
```powershell
# Open test page first
start test.html

# Click "Check Backend Health"
# Then go to main app
```

---

## 🌟 FEATURES SUMMARY

✅ Dynamic location input with autocomplete
✅ Google Distance Matrix API integration
✅ TSP solver (2 algorithms)
✅ Interactive Google Maps
✅ Distance matrix visualization
✅ Responsive design
✅ Error handling
✅ Production-ready code
✅ Complete documentation
✅ Testing utilities

---

**Your application is production-ready and waiting to start! 🚀**

*Run `run.bat` or `python app.py` to begin!*
