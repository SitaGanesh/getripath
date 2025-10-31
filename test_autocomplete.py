#!/usr/bin/env python
"""Quick test script to verify autocomplete and geocoding endpoints."""
import os
from dotenv import load_dotenv
import requests

# Load environment from .env for local development/tests
load_dotenv()

# Backend URL used by the tests (can be overridden via .env)
BACKEND = os.environ.get('BACKEND_URL', 'http://localhost:5000')

def test_autocomplete(query):
    print(f"\n=== Testing autocomplete: '{query}' ===")
    try:
        resp = requests.get(f'{BACKEND}/autocomplete', params={'q': query, 'limit': 3}, timeout=10)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        if 'error' in data:
            print(f"Error: {data['error']}")
        else:
            suggestions = data.get('suggestions', [])
            print(f"Got {len(suggestions)} suggestions:")
            for s in suggestions:
                print(f"  - {s['display_name']}")
                print(f"    ({s['lat']:.4f}, {s['lon']:.4f})")
    except Exception as e:
        print(f"Request failed: {e}")

def test_calculate_route(locations):
    print(f"\n=== Testing calculate-route: {locations} ===")
    try:
        resp = requests.post(f'{BACKEND}/calculate-route', 
                            json={'locations': locations},
                            timeout=60)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        if 'error' in data:
            print(f"Error: {data['error']}")
        else:
            print(f"Total distance: {data['total_distance']:.2f} km")
            print(f"Optimal path: {' -> '.join(data['optimal_path'])}")
            # Show distance matrix summary
            matrix = data.get('distance_matrix', [])
            if matrix:
                print("\nDistance matrix:")
                for i, row in enumerate(matrix):
                    print(f"  {locations[i]}: {row}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == '__main__':
    print("Testing Distance Optimizer Backend\n")
    print("Make sure the Flask server is running on http://localhost:5000\n")
    
    # Test autocomplete
    test_autocomplete('goa')
    test_autocomplete('mumbai')
    
    # Test route calculation
    test_calculate_route(['goa', 'mumbai'])
    
    print("\n=== Tests complete ===")
