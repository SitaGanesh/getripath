# app.py - Flask Backend for TSP Distance Optimizer
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
import requests
import itertools
from typing import List, Tuple
import math
import time
import os
import json

# Enable CORS for frontend communication

# Load environment variables from .env if present
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication
CORS(app)  # Enable CORS for frontend communication

# Google Distance Matrix API configuration
# Config from environment (use .env in development)
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
DISTANCE_MATRIX_URL = os.environ.get('GOOGLE_DISTANCE_MATRIX_URL', 'https://maps.googleapis.com/maps/api/distancematrix/json')

# External services (override with env vars for production)
PHOTON_URL = os.environ.get('PHOTON_URL', 'https://photon.komoot.io/api')
NOMINATIM_SEARCH_URL = os.environ.get('NOMINATIM_SEARCH_URL', 'https://nominatim.openstreetmap.org/search')
OSRM_BASE_URL = os.environ.get('OSRM_BASE_URL', 'https://router.project-osrm.org')


class TSPSolver:
    """
    Traveling Salesman Problem Solver using Nearest Neighbor algorithm
    """

    def __init__(self, locations: List[str],
                 distance_matrix: List[List[float]]):
        """
        Initialize TSP Solver with locations and distance matrix

        Args:
            locations: List of location names
            distance_matrix: 2D matrix of distances between locations
        """
        self.locations = locations
        self.distance_matrix = distance_matrix
        self.n = len(locations)

    def nearest_neighbor(self, start_index: int = 0) -> (
            Tuple[List[int], float]):
        """
        Solve TSP using Nearest Neighbor heuristic

        Args:
            start_index: Starting location index

        Returns:
            Tuple of (path indices, total distance)
        """
        unvisited = set(range(self.n))
        current = start_index
        path = [current]
        unvisited.remove(current)
        total_distance = 0.0

        while unvisited:
            nearest = min(
                unvisited,
                key=lambda x: self.distance_matrix[current][x]
            )
            total_distance += self.distance_matrix[current][nearest]
            current = nearest
            path.append(current)
            unvisited.remove(current)

        # Return to start
        total_distance += self.distance_matrix[current][start_index]
        path.append(start_index)

        return path, total_distance

    def solve_all_starting_points(self) -> Tuple[List[str], float]:
        """
        Try starting from each location and return the best route

        Returns:
            Tuple of (optimal path as location names, total distance)
        """
        best_path = None
        best_distance = float('inf')

        for start_idx in range(self.n):
            path_indices, distance = self.nearest_neighbor(start_idx)
            if distance < best_distance:
                best_distance = distance
                best_path = path_indices

        # Convert indices to location names
        optimal_path = [self.locations[i] for i in best_path]

        return optimal_path, best_distance

    def solve_optimal(self) -> Tuple[List[str], float]:
        """
        For small number of locations (<=10), try all permutations
        for truly optimal solution. For larger sets, use nearest
        neighbor heuristic

        Returns:
            Tuple of (optimal path as location names, total distance)
        """
        if self.n <= 10:
            return self._brute_force_optimal()
        else:
            return self.solve_all_starting_points()

    def _brute_force_optimal(self) -> Tuple[List[str], float]:
        """
        Brute force solution for small TSP instances

        Returns:
            Tuple of (optimal path as location names, total distance)
        """
        min_distance = float('inf')
        best_path = None

        # Try all permutations starting from location 0
        for perm in itertools.permutations(range(1, self.n)):
            path = [0] + list(perm)
            distance = self._calculate_path_distance(path)

            if distance < min_distance:
                min_distance = distance
                best_path = path

        # Add return to start
        best_path.append(0)
        optimal_path = [self.locations[i] for i in best_path]

        return optimal_path, min_distance

    def _calculate_path_distance(self, path: List[int]) -> float:
        """
        Calculate total distance for a given path

        Args:
            path: List of location indices

        Returns:
            Total distance
        """
        total = 0.0
        for i in range(len(path) - 1):
            total += self.distance_matrix[path[i]][path[i + 1]]
        # Add return to start
        total += self.distance_matrix[path[-1]][path[0]]
        return total



class DistanceMatrixCalculator:
    """
    Calculate distance matrix using Google Distance Matrix API
    """

    def __init__(self, api_key: str):
        """
        Initialize with Google API key

        Args:
            api_key: Google Distance Matrix API key
        """
        self.api_key = api_key
        # Headers for Nominatim requests (policy requires a valid User-Agent)
        self.nominatim_headers = {
            'User-Agent': 'DistanceOptimalityProblem/1.0 (contact@example.com)'
        }
        # Simple in-memory cache for geocoding to reduce Nominatim calls
        # Key: normalized location string -> (lat, lon)
        self._geocode_cache = {}
        # Minimum delay between Nominatim requests (seconds) - INCREASED to avoid 403
        self._nominatim_delay = 2.0  # Was 1.0, increased due to rate limiting
    # Photon (Komoot) autocomplete/geocoding endpoint and India bbox to bias results
    # Use environment-configured PHOTON_URL where possible
        self._photon_url = os.environ.get('PHOTON_URL', PHOTON_URL)
        self._india_bbox = "68.0,6.5,97.5,35.5"
        # Disk cache path
        self._cache_path = os.path.join(os.path.dirname(__file__), 'geocode_cache.json')
        # Load cache from disk if present
        try:
            if os.path.isfile(self._cache_path):
                with open(self._cache_path, 'r', encoding='utf-8') as fh:
                    raw = json.load(fh)
                    # Expect mapping str -> [lat, lon]
                    for k, v in raw.items():
                        if isinstance(v, list) and len(v) >= 2:
                            self._geocode_cache[k] = (float(v[0]), float(v[1]))
        except Exception as e:
            print(f"Failed to load geocode cache: {e}")

    def get_distance_matrix(self, locations: List[str]) -> (
            List[List[float]]):
        """
        Get distance matrix for given locations using Google Distance
        Matrix API

        Args:
            locations: List of location names

        Returns:
            2D distance matrix in kilometers
        """
        # New approach: use Nominatim to geocode each location into lat/lon
        # then use OSRM table API to compute driving distances between all
        # coordinates in one request. This returns distances in meters.
        n = len(locations)
        distance_matrix = [[0.0] * n for _ in range(n)]

        try:
            coords = self._geocode_locations_nominatim(locations)
            print(f"Geocoded {len(coords)} locations:")
            for i, (loc, (lat, lon)) in enumerate(zip(locations, coords)):
                print(f"  [{i}] {loc} -> ({lat:.4f}, {lon:.4f})")
            
            # coords is list of (lat, lon)
            # Build coords string as lon,lat;lon,lat;...
            coord_pairs = ['{:.6f},{:.6f}'.format(lon, lat) for (lat, lon) in coords]
            coord_str = ';'.join(coord_pairs)

            # Use configurable OSRM base URL
            osrm_url = f'{OSRM_BASE_URL}/table/v1/driving/{coord_str}'
            print(f"OSRM request URL: {osrm_url}")
            params = {'annotations': 'distance'}
            # Use retry/backoff helper
            resp = self._requests_with_retries(osrm_url, params=params, timeout=30)
            data = resp.json()
            print(f"OSRM response code: {data.get('code')}, message: {data.get('message', 'N/A')}")

            # If OSRM didn't return distances, log full response for debugging
            if 'distances' not in data or data['distances'] is None:
                print("OSRM table response (no distances):", resp.status_code, resp.text[:500])
                # As a fallback, perform pairwise route lookups for all pairs
                print("Falling back to pairwise OSRM route lookups for all pairs...")
                for i in range(n):
                    for j in range(n):
                        if i == j:
                            distance_matrix[i][j] = 0.0
                            continue
                        try:
                            lat1, lon1 = coords[i]
                            lat2, lon2 = coords[j]
                            route_url = f'{OSRM_BASE_URL}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}'
                            route_resp = self._requests_with_retries(route_url, params={'overview': 'false'}, timeout=15, max_retries=3, backoff=0.5)
                            route_data = route_resp.json()
                            if route_data.get('code') == 'Ok' and 'routes' in route_data and route_data['routes']:
                                dist_m = route_data['routes'][0].get('distance', None)
                                if dist_m is not None:
                                    distance_matrix[i][j] = float(dist_m) / 1000.0
                                    continue
                        except Exception as ex:
                            print(f"Pairwise fallback failed for i={i} j={j}: {ex}")
                        # If we get here, mark unreachable for now
                        distance_matrix[i][j] = 999999.0

            # OSRM returns distances in meters; convert to kilometers
            has_nulls = False
            for i in range(n):
                for j in range(n):
                    v = data['distances'][i][j]
                    if v is None:
                        has_nulls = True
                        # unreachable; set a large value and log
                        print(f"OSRM table: unreachable pair i={i} j={j}")
                        distance_matrix[i][j] = 999999.0
                    else:
                        distance_matrix[i][j] = float(v) / 1000.0
                        
            print(f"Distance matrix from OSRM table:")
            for i in range(n):
                print(f"  {locations[i]}: {distance_matrix[i]}")

            # If we got nulls, try pairwise route lookups for missing pairs
            if has_nulls:
                print(f"Attempting pairwise OSRM route lookups for {sum(1 for i in range(n) for j in range(n) if i != j and distance_matrix[i][j] >= 999999.0)} unreachable pairs...")
                count = 0
                for i in range(n):
                    for j in range(n):
                        if i != j and distance_matrix[i][j] >= 999999.0:
                            count += 1
                            try:
                                lat1, lon1 = coords[i]
                                lat2, lon2 = coords[j]
                                route_url = f'{OSRM_BASE_URL}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}'
                                # try a couple of retries for pairwise queries
                                route_resp = self._requests_with_retries(route_url, params={'overview': 'false'}, timeout=15, max_retries=4, backoff=0.5)
                                route_data = route_resp.json()
                                if route_data.get('code') == 'Ok' and 'routes' in route_data and route_data['routes']:
                                    dist_m = route_data['routes'][0].get('distance', None)
                                    if dist_m is not None:
                                        distance_matrix[i][j] = float(dist_m) / 1000.0
                                        print(f"  [{count}] Pairwise {locations[i]} -> {locations[j]}: {distance_matrix[i][j]:.2f} km")
                                    else:
                                        print(f"  [{count}] Pairwise {locations[i]} -> {locations[j]}: no distance in route")
                                else:
                                    print(f"  [{count}] Pairwise {locations[i]} -> {locations[j]}: {route_data.get('code', 'error')} - {route_data.get('message', '')}")
                            except Exception as ex:
                                print(f"  [{count}] Pairwise {locations[i]} -> {locations[j]} failed: {ex}")
                                # Keep the sentinel value

            return distance_matrix

        except Exception as e:
            # Log the error and fallback to Haversine (approximate)
            import traceback
            print(f"❌ Error building distance matrix via OSM/OSRM: {e}")
            print("Traceback:")
            traceback.print_exc()
            print("\nAttempting Haversine fallback...")
            return self._get_haversine_matrix(locations)

    def _fetch_batch_distances(self, origins: List[str],
                                destinations: List[str]) -> List[
                                    List[float]]:
        """
        Fetch distances for a batch of origins and destinations

        Args:
            origins: List of origin locations
            destinations: List of destination locations

        Returns:
            2D distance matrix for the batch
        """
        # This method is no longer used when OSRM is available. Keep it for
        # backward compatibility, but raise to indicate it's deprecated.
        raise NotImplementedError("_fetch_batch_distances is deprecated; using OSRM table and Nominatim instead.")

    def _geocode_locations_nominatim(self, locations: List[str]) -> List[Tuple[float, float]]:
        """
        Geocode a list of location strings using Nominatim (OpenStreetMap)

        Returns list of (lat, lon) tuples. Raises if any location cannot be
        geocoded.
        """
        coords = []
        for loc in locations:
            norm = loc.strip().lower()
            # Check cache first
            if norm in self._geocode_cache:
                coords.append(self._geocode_cache[norm])
                continue

            # Try a couple of query variants and use retries
            tried = []
            success = False
            # First, try Photon (better for autocomplete/geocoding, less strict rate limits)
            try:
                p_params = {'q': loc, 'limit': 1, 'lang': 'en', 'bbox': self._india_bbox}
                pr = self._requests_with_retries(self._photon_url, params=p_params, timeout=8, max_retries=2, backoff=0.2)
                pjson = pr.json()
                features = pjson.get('features', []) if isinstance(pjson, dict) else []
                if features:
                    f0 = features[0]
                    geom = f0.get('geometry', {})
                    coords_arr = geom.get('coordinates', None)
                    if coords_arr and len(coords_arr) >= 2:
                        lon = float(coords_arr[0]); lat = float(coords_arr[1])
                        coords.append((lat, lon))
                        self._geocode_cache[norm] = (lat, lon)
                        try:
                            with open(self._cache_path, 'w', encoding='utf-8') as fh:
                                json.dump({k: [v[0], v[1]] for k, v in self._geocode_cache.items()}, fh)
                        except Exception:
                            pass
                        # Photon is fast; small sleep to be polite
                        time.sleep(0.05)
                        print(f"Geocoded '{loc}' via Photon -> ({lat:.4f}, {lon:.4f})")
                        success = True
            except Exception as ex:
                # Photon failed for this query; we'll fall back to Nominatim below
                tried.append((loc, 'photon_error', str(ex)))
            # If Photon succeeded, skip Nominatim variants
            if success:
                continue
            # Try multiple query variants using Photon first (avoid Nominatim rate limits)
            variants = [
                loc,
                f"{loc}, India",
                f"{loc}, Maharashtra, India",
                f"{loc}, Karnataka, India",
                f"{loc}, Goa, India"
            ]
            for q in variants:
                try:
                    p_params = {'q': q, 'limit': 1, 'lang': 'en', 'bbox': self._india_bbox}
                    pr = self._requests_with_retries(self._photon_url, params=p_params, timeout=8, max_retries=2, backoff=0.2)
                    pjson = pr.json()
                    features = pjson.get('features', []) if isinstance(pjson, dict) else []
                    tried.append((q, getattr(pr, 'status_code', None), len(features)))
                    if features:
                        f0 = features[0]
                        geom = f0.get('geometry', {})
                        coords_arr = geom.get('coordinates', None)
                        if coords_arr and len(coords_arr) >= 2:
                            lon = float(coords_arr[0]); lat = float(coords_arr[1])
                            coords.append((lat, lon))
                            self._geocode_cache[norm] = (lat, lon)
                            try:
                                with open(self._cache_path, 'w', encoding='utf-8') as fh:
                                    json.dump({k: [v[0], v[1]] for k, v in self._geocode_cache.items()}, fh)
                            except Exception:
                                pass
                            time.sleep(0.05)
                            print(f"Geocoded '{loc}' via Photon variant '{q}' -> ({lat:.4f}, {lon:.4f})")
                            success = True
                            break
                except Exception as ex:
                    tried.append((q, 'photon_variant_error', str(ex)))

            # If Photon variants didn't find anything, fall back to Nominatim variants
            if success:
                continue
            for q in variants:
                try:
                    params = {'q': q, 'format': 'json', 'addressdetails': 1, 'limit': 1, 'countrycodes': 'in'}
                    r = self._requests_with_retries(NOMINATIM_SEARCH_URL, params=params, timeout=15, max_retries=2, backoff=2.0)
                    results = r.json()
                    tried.append((q, getattr(r, 'status_code', None), len(results) if results else 0))
                    if results:
                        first = results[0]
                        lat = float(first['lat'])
                        lon = float(first['lon'])
                        coords.append((lat, lon))
                        # store in cache and persist
                        self._geocode_cache[norm] = (lat, lon)
                        print(f"Geocoded '{loc}' -> ({lat:.4f}, {lon:.4f}) using query: '{q}'")
                        try:
                            with open(self._cache_path, 'w', encoding='utf-8') as fh:
                                json.dump({k: [v[0], v[1]] for k, v in self._geocode_cache.items()}, fh)
                        except Exception as _e:
                            print("Warning: failed to write geocode cache:", _e)
                        time.sleep(self._nominatim_delay)
                        success = True
                        break
                    else:
                        # No results for this query, wait before trying next variant
                        time.sleep(self._nominatim_delay)
                except Exception as ex:
                    # record and try next variant
                    error_msg = str(ex)
                    tried.append((q, error_msg, 0))
                    # If we hit a 403, wait longer before next attempt
                    if '403' in error_msg or 'Forbidden' in error_msg:
                        print(f"⚠️ Nominatim rate limit hit for '{q}'. Waiting 5 seconds...")
                        time.sleep(5.0)
                    else:
                        time.sleep(self._nominatim_delay)
            if not success:
                # If still not found, raise with details
                print(f"Failed to geocode '{loc}'. All attempts: {tried}")
                raise Exception(f"Failed to geocode '{loc}'. Attempts: {len(tried)}")

        return coords

    def _get_haversine_matrix(self, locations: List[str]) -> (
            List[List[float]]):
        """
        Fallback: Calculate distances using Haversine formula
        (requires geocoding). This is a simplified fallback - in
        production, you'd want to geocode first

        Args:
            locations: List of location names

        Returns:
            2D distance matrix (approximate)
        """
        # Fallback: attempt to geocode and compute Haversine distances
        try:
            coords = self._geocode_locations_nominatim(locations)
            n = len(coords)
            matrix = [[0.0] * n for _ in range(n)]
            for i in range(n):
                lat1, lon1 = coords[i]
                for j in range(n):
                    if i == j:
                        matrix[i][j] = 0.0
                    else:
                        lat2, lon2 = coords[j]
                        matrix[i][j] = self._haversine_km(lat1, lon1, lat2, lon2)
            return matrix
        except Exception as e:
            print(f"Haversine fallback failed geocoding: {e}")
            # final fallback: keep previous dummy but make it clearly wrong-large
            n = len(locations)
            return [[0.0 if i == j else 999999.0 for j in range(n)] for i in range(n)]

    def _haversine_km(self, lat1, lon1, lat2, lon2):
        # Haversine formula to compute great-circle distance
        R = 6371.0  # Earth radius in km
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2.0)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def _requests_with_retries(self, url, params=None, timeout=30, max_retries=3, backoff=1.0, **kwargs):
        """
        Simple requests.get wrapper with retries and exponential backoff.
        Returns requests.Response or raises the last exception.
        """
        attempt = 0
        while True:
            try:
                r = requests.get(url, params=params, timeout=timeout, **kwargs)
                # If status code is 429 or 5xx, consider retrying
                if r.status_code == 429 or 500 <= r.status_code < 600:
                    raise requests.HTTPError(f"Status {r.status_code}")
                r.raise_for_status()
                return r
            except Exception as e:
                attempt += 1
                if attempt >= max_retries:
                    print(
                        "Request failed after {} attempts to {}: {}".format(
                            attempt, url, e
                        )
                    )
                    raise
                # exponential backoff with jitter
                sleep_for = backoff * (2 ** (attempt - 1))
                jitter = (0.5 - os.urandom(1)[0] / 255.0) * 0.5 * sleep_for
                sleep_total = max(0.5, sleep_for + jitter)
                print(
                    "Request failed (attempt {}) to {}: {}. Retrying in {:.1f}s".format(
                        attempt, url, e, sleep_total
                    )
                )
                time.sleep(sleep_total)



@app.route('/')
def home():
    """Home endpoint.

    Behavior:
    - If the client accepts HTML (browser), redirect to the frontend UI at `/ui/`.
    - Otherwise return the API index JSON for programmatic clients.
    """
    # If this is a browser (Accept header includes text/html), redirect to the UI
    if request.accept_mimetypes and request.accept_mimetypes.accept_html:
        return redirect('/ui/')

    return jsonify({
        'message': 'TSP Distance Optimizer API',
        'version': '1.0',
        'endpoints': {
            '/calculate-route': (
                'POST - Calculate optimal route for given locations'
            ),
            '/health': 'GET - Health check'
        }
    })


@app.route('/health')
def health():
    """Health check endpoint used by tests and monitoring."""
    return jsonify({'status': 'ok', 'version': '1.0'}), 200


# Serve the single-file web UI and assets under /ui/ so users can browse
# http://localhost:5000/ui/ instead of opening index.html via file://.
@app.route('/ui/', defaults={'path': 'index.html'})
@app.route('/ui/<path:path>')
def serve_ui(path):
    """ This url path shows the complete frontend of our website by loading the html content as a path an alternate way to run file"""
    base = os.path.dirname(__file__)
    full = os.path.join(base, path)
    if os.path.isfile(full):
        return send_from_directory(base, path)
    return jsonify({'error': 'Not found'}), 404


# ---------- Helper: Nominatim search (geocoding) ----------
@app.route('/search')
def search_location():
    """ This is type 1 search of our website, where it takes one of the parameter, based on that it will search, if we go to localhost/search?q=hyderabad it gives the complete location address with latitute, longitude and many more additional."""
    q = request.args.get('q', '')
    if not q:
        return jsonify({'error': 'Query parameter q is required'}), 400

    url = NOMINATIM_SEARCH_URL
    params = {'q': q, 'format': 'json', 'addressdetails': 1, 'limit': 1}
    headers = {'User-Agent': 'DistanceOptimalityProblem/1.0 (contact@example.com)'}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"Nominatim search error for '{q}': {e}")
        return jsonify({'error': 'Geocoding request failed', 'detail': str(e)}), 502

    if not data:
        return jsonify({'error': 'Location not found'}), 404

    first = data[0]
    return jsonify({
        'place': first.get('display_name'),
        'lat': float(first.get('lat')),
        'lon': float(first.get('lon')),
        'raw': first
    })


@app.route('/autocomplete')
def autocomplete():
    """This function is better than Nominatim, where it takes the advance locations incluing cities, towns, anythings out of box with suggestion field included, where it suggestus what the user wanted to type. Return place suggestions using Photon (Komoot) - better for autocomplete than Nominatim.

    Query params:
      q - search text (required)
      limit - optional (default 8)
    """
    q = request.args.get('q', '')
    if not q or q.strip() == '':
        return jsonify({'suggestions': []})

    try:
        limit = int(request.args.get('limit', 12))
    except Exception:
        limit = 12

    # Use Photon API (Komoot) - optimized for autocomplete, fewer rate limits
    photon_url = PHOTON_URL
    
    # Bbox for India (approx) to bias results to India
    # Format: lon_min,lat_min,lon_max,lat_max
    india_bbox = "68.0,6.5,97.5,35.5"
    
    params = {
        'q': q,
        'limit': limit,
        'lang': 'en',
        'bbox': india_bbox
    }
    
    headers = {
        'User-Agent': 'DistanceOptimalityProblem/1.0 (contact@example.com)'
    }

    try:
        resp = requests.get(photon_url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"Photon autocomplete error for '{q}': {e}")
        # Fallback to Nominatim if Photon fails
        return autocomplete_nominatim_fallback(q, limit)

    suggestions = []
    features = data.get('features', [])
    
    for feature in features:
        try:
            props = feature.get('properties', {})
            geom = feature.get('geometry', {})
            coords = geom.get('coordinates', [None, None])
            lon, lat = coords[0], coords[1]
            
            if lat is None or lon is None:
                continue
            
            # Build display name from properties
            name_parts = []
            if props.get('name'):
                name_parts.append(props['name'])
            if props.get('city') and props.get('city') != props.get('name'):
                name_parts.append(props['city'])
            if props.get('state'):
                name_parts.append(props['state'])
            if props.get('country'):
                name_parts.append(props['country'])
            
            display_name = ', '.join(name_parts) if name_parts else props.get('name', 'Unknown')
            
            suggestions.append({
                'display_name': display_name,
                'name': props.get('name', ''),
                'lat': float(lat),
                'lon': float(lon),
                'type': props.get('type', ''),
                'osm_type': props.get('osm_type', ''),
                'city': props.get('city', ''),
                'state': props.get('state', ''),
                'country': props.get('country', '')
            })
        except Exception as ex:
            print(f"Error parsing Photon feature: {ex}")
            continue

    return jsonify({'suggestions': suggestions})


def autocomplete_nominatim_fallback(q, limit=8):
    """Fallback to Nominatim if Photon fails."""
    calc = DistanceMatrixCalculator(GOOGLE_API_KEY)
    url = NOMINATIM_SEARCH_URL
    params = {
        'q': q,
        'format': 'json',
        'addressdetails': 1,
        'limit': limit,
        'countrycodes': 'in'
    }

    try:
        resp = calc._requests_with_retries(url, params=params, timeout=10,
                                           max_retries=2, backoff=0.4,
                                           headers=calc.nominatim_headers)
        results = resp.json()
    except Exception as e:
        print(f"Nominatim fallback error for '{q}': {e}")
        return jsonify({'error': 'Autocomplete request failed', 'detail': str(e)}), 502

    suggestions = []
    for r in results:
        try:
            suggestions.append({
                'display_name': r.get('display_name'),
                'lat': float(r.get('lat')),
                'lon': float(r.get('lon')),
                'type': r.get('type')
            })
        except Exception:
            continue

    return jsonify({'suggestions': suggestions})


# ---------- 2 Haversine Distance (quick approx) ----------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat/2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon/2) ** 2)
    return round(R * 2 * math.asin(math.sqrt(a)), 2)


@app.route('/distance')
def get_distance():
    """ Calculates teh distance between the locations/places using the variables and values based on latitude and longitude"""
    try:
        lat1 = float(request.args.get('lat1'))
        lon1 = float(request.args.get('lon1'))
        lat2 = float(request.args.get('lat2'))
        lon2 = float(request.args.get('lon2'))
    except Exception:
        return jsonify({'error': 'lat1, lon1, lat2, lon2 query params required and must be floats'}), 400

    km = haversine(lat1, lon1, lat2, lon2)
    return jsonify({'distance_km': km, 'estimated_cost_₹': round(km * 14, 2)})


# ---------- 3 Routing using OSRM (driving route) ----------
@app.route('/route')
def route():
    """Used to show the distances on the on the map based on the coordinates """
    try:
        lat1 = float(request.args.get('lat1'))
        lon1 = float(request.args.get('lon1'))
        lat2 = float(request.args.get('lat2'))
        lon2 = float(request.args.get('lon2'))
    except Exception:
        return jsonify({'error': 'lat1, lon1, lat2, lon2 query params required and must be floats'}), 400

    osrm_url = f'{OSRM_BASE_URL}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}'
    params = {'overview': 'full', 'geometries': 'geojson'}

    try:
        # Use DistanceMatrixCalculator helper for retries/backoff
        calculator = DistanceMatrixCalculator(GOOGLE_API_KEY)
        resp = calculator._requests_with_retries(osrm_url, params=params, timeout=20)
        data = resp.json()
    except Exception as e:
        print(f"OSRM routing error: {e}")
        return jsonify({'error': 'Routing request failed', 'detail': str(e)}), 502

    if 'routes' not in data or not data['routes']:
        return jsonify({'error': 'Routing failed'}), 500

    route0 = data['routes'][0]
    return jsonify({
        'distance_km': round(route0.get('distance', 0) / 1000.0, 2),
        'duration_min': round(route0.get('duration', 0) / 60.0, 2),
        'geometry': route0.get('geometry', {}).get('coordinates', [])
    })


@app.route('/nearest-neighbor', methods=['POST'])
def nearest_neighbor_route():
    """
    Server-side nearest neighbor endpoint.

    Request JSON:
      { "locations": [..], "start_index": optional int }

    Returns the NN path (indices and location names) and total distance.
    """
    try:
        data = request.get_json()
        if not data or 'locations' not in data:
            return jsonify({'error': 'Missing locations in request body'}), 400

        locations = [l.strip() for l in data['locations'] if l and l.strip()]
        if len(locations) < 2:
            return jsonify({'error': 'At least 2 locations are required'}), 400

        start_index = data.get('start_index', None)
        if start_index is not None:
            try:
                start_index = int(start_index)
            except Exception:
                start_index = None

        calculator = DistanceMatrixCalculator(GOOGLE_API_KEY)
        distance_matrix = calculator.get_distance_matrix(locations)

        solver = TSPSolver(locations, distance_matrix)
        if start_index is None:
            # Try all starting points and return best
            best_path = None
            best_distance = float('inf')
            for si in range(len(locations)):
                path_idx, dist = solver.nearest_neighbor(si)
                if dist < best_distance:
                    best_distance = dist
                    best_path = path_idx
            path_indices = best_path
            total_distance = best_distance
        else:
            path_indices, total_distance = solver.nearest_neighbor(start_index)

        path_names = [locations[i] for i in path_indices]
        return jsonify({
            'path_indices': path_indices,
            'path_names': path_names,
            'total_distance': total_distance,
            'distance_matrix': distance_matrix
        })
    except Exception as e:
        print(f"Error in nearest_neighbor endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/calculate-route', methods=['POST'])
def calculate_route():
    """
    Calculate optimal route for given locations

    Request body:
    {
        "locations": ["Location1", "Location2", ...]
    }

    Response:
    {
        "locations": [...],
        "optimal_path": [...],
        "total_distance": float,
        "distance_matrix": [[...]]
    }
    """
    try:
        data = request.get_json()

        if not data or 'locations' not in data:
            return jsonify({
                'error': 'Missing locations in request body'
            }), 400

        locations = data['locations']

        if len(locations) < 2:
            return jsonify({
                'error': 'At least 2 locations are required'
            }), 400

        if len(locations) > 25:
            return jsonify({
                'error': 'Maximum 25 locations allowed'
            }), 400

        # Clean location names
        locations = [loc.strip() for loc in locations if loc.strip()]

        print(f"Calculating route for {len(locations)} locations...")

        # Step 1: Get distance matrix from Google API
        calculator = DistanceMatrixCalculator(GOOGLE_API_KEY)
        distance_matrix = calculator.get_distance_matrix(locations)

        print("Distance matrix calculated successfully")

    # Step 2: Solve TSP
        solver = TSPSolver(locations, distance_matrix)
        optimal_path, total_distance = solver.solve_optimal()

        print(f"Optimal path found with distance: {total_distance:.2f} km")

        # Step 3: Also include coordinates used for each location (lat, lon)
        try:
            coords = calculator._geocode_locations_nominatim(locations)
        except Exception:
            coords = []

        # Step 4: Return results
        algorithm = (
            'brute_force' if len(locations) <= 10
            else 'nearest_neighbor'
        )
        return jsonify({
            'locations': locations,
            'optimal_path': optimal_path,
            'total_distance': total_distance,
            'distance_matrix': distance_matrix,
            'coords': coords,
            'algorithm_used': algorithm
        })

    except Exception as e:
        print(f"Error in calculate_route: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("TSP Distance Optimizer Backend Server")
    print("=" * 60)
    print("Server starting on http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5000)

