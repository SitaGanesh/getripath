# Distance Optimality Problem — README

Introduction
------------

This web app computes driving routes for multiple places. It geocodes place names (Photon → Nominatim), builds an OSRM distance matrix, solves a route using a TSP solver (nearest-neighbor or brute-force for small sets), and shows results on a Leaflet map.

Local setup (step-by-step)
--------------------------

1) Fork (optional) and clone

```powershell
# Fork on GitHub (optional) then clone:
git clone <your-repo-url>
cd DistanceOptimalityProblem
```

2) Create & activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3) Install dependencies

```powershell
pip install -r requirements.txt
```

4) Create a `.env` file with the variables used by the app

Create `.env` at the project root and paste these keys (example values):

```text
PHOTON_URL=https://photon.komoot.io/api
NOMINATIM_SEARCH_URL=https://nominatim.openstreetmap.org/search
OSRM_BASE_URL=https://router.project-osrm.org
GOOGLE_API_KEY=
GOOGLE_DISTANCE_MATRIX_URL=
BACKEND_URL=http://localhost:5000
```

These names match the environment variables read in `app.py`.

5) Run the backend

```powershell
python app.py
```

6) Open the frontend

- Preferred: open the served UI at `http://localhost:5000/ui/`
- Alternative: open the local `index.html` or run `run.bat` / `start.bat` which launch the backend and open the UI.

What to expect in the UI
------------------------

- Type a location in the input; autocomplete suggestions appear.
- Add multiple locations (one-per-line) and reorder if needed.
- Click "Calculate" to compute the route — you will see progress, the route on the map, total distance, and an option to export CSV.

Tests
-----

```powershell
python -m unittest -v
# Backend integration tests (backend must be running):
python test_backend.py
```

Function / endpoint descriptions
--------------------------------

`/search` — Geocoding
- Input: `q` query param. Calls Nominatim and returns display name, lat, lon and raw result.

`/autocomplete` — Suggestions
- Input: `q` (and optional `limit`). Uses Photon (Komoot) with an India-biased bbox and returns suggestion list. Falls back to Nominatim when needed.

`haversine()` — Approx distance
- Computes great-circle (km) between two lat/lon pairs. Used as a fallback estimate.

`/distance` — Pairwise distance
- Input: `lat1, lon1, lat2, lon2`. Returns haversine distance and an estimated cost value.

`/route` — OSRM driving route
- Input: `lat1, lon1, lat2, lon2`. Calls OSRM `/route` and returns distance (km), duration (min), and geometry coordinates for mapping.

`/nearest-neighbor` — NN TSP solver
- Input: JSON `{ "locations": [...] }`. Builds distance matrix (OSRM table + pairwise fallbacks) and returns NN path indices/names and total distance.

`/calculate-route` — Main orchestration
- Input: JSON `{ "locations": [...] }`. Geocodes locations, builds OSRM distance matrix, fills missing pairs via pairwise routes, runs the TSP solver (brute-force when ≤10 locations), and returns `optimal_path`, `total_distance`, `distance_matrix`, and `coords`.

Troubleshooting (short)
----------------------

- `999999` distances: indicates unreachable pairs or missing geocodes — check `geocode_cache.json` and `OSRM_BASE_URL`.
- Nominatim 403: rate-limited. Wait, use cached coordinates, or host your own geocoder for heavy usage.
- Autocomplete fails: verify `PHOTON_URL`, network access, and that the backend is running.

Deploy (very short)
-------------------

- Use a WSGI server (example Procfile for Render):

```text
web: gunicorn app:app --bind 0.0.0.0:$PORT
```

Thanks — Sita Ganesh

