"""Direct OSRM test to debug the distance matrix issue."""
import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()

# Use configurable OSRM base URL so tests can run against a local OSRM server
OSRM_BASE = os.environ.get('OSRM_BASE_URL', 'http://router.project-osrm.org')

# Goa coordinates: 15.3005, 74.0855
# Mumbai coordinates: 19.0550, 72.8692

coords = [
    (15.3005, 74.0855),  # Goa
    (19.0550, 72.8692),   # Mumbai
    (17.3871, 78.4917), # Hyderabad
]

# Build OSRM table URL (lon,lat format!)
coord_str = ';'.join([f'{lon:.6f},{lat:.6f}' for (lat, lon) in coords])
table_url = f"{OSRM_BASE}/table/v1/driving/{coord_str}"

print("Testing OSRM table API\n")
print(f"Coordinates:")
print(f"  Goa: {coords[0]}")
print(f"  Mumbai: {coords[1]}")
print(f"  Hyderabad: {coords[2]}")
print(f"\nOSRM URL: {table_url}")
print(f"Params: annotations=distance\n")

try:
    resp = requests.get(table_url, params={'annotations': 'distance'}, timeout=30)
    print(f"Status code: {resp.status_code}")
    data = resp.json()
    print(f"\nResponse JSON:")
    print(json.dumps(data, indent=2))
    
    if 'distances' in data:
        print(f"\nDistance matrix (meters):")
        for i, row in enumerate(data['distances']):
            print(f"  Row {i}: {row}")
            for j, dist in enumerate(row):
                if dist is not None:
                    print(f"    [{i}]->[{j}]: {dist/1000:.2f} km")
                else:
                    print(f"    [{i}]->[{j}]: NULL (unreachable)")
    else:
        print("\n❌ No 'distances' key in response!")
        
except Exception as e:
    print(f"\n❌ Request failed: {e}")

# Also test pairwise route
print("\n" + "="*60)
print("Testing pairwise route API\n")

route_url = f"{OSRM_BASE}/route/v1/driving/{coords[0][1]},{coords[0][0]};{coords[1][1]},{coords[1][0]}"
print(f"Route URL: {route_url}\n")

try:
    resp = requests.get(route_url, params={'overview': 'false'}, timeout=15)
    print(f"Status code: {resp.status_code}")
    data = resp.json()
    print(f"\nResponse code: {data.get('code')}")
    print(f"Message: {data.get('message', 'N/A')}")
    
    if 'routes' in data and data['routes']:
        route = data['routes'][0]
        dist = route.get('distance')
        duration = route.get('duration')
        print(f"\nRoute found!")
        print(f"  Distance: {dist/1000:.2f} km" if dist else "  Distance: N/A")
        print(f"  Duration: {duration/60:.1f} min" if duration else "  Duration: N/A")
    else:
        print("\n❌ No routes in response!")
        
except Exception as e:
    print(f"\n❌ Request failed: {e}")
