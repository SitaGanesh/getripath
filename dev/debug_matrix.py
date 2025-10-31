"""Dev helper to test DistanceMatrixCalculator directly (dev copy).
"""
import os
import sys
sys.path.insert(0, '..')

from app import DistanceMatrixCalculator

print("="*60)
print("Dev: Testing DistanceMatrixCalculator directly")
print("="*60)

api_key = os.environ.get('GOOGLE_API_KEY', '')
calc = DistanceMatrixCalculator(api_key)

locations = ['goa', 'mumbai']
print(f"\nLocations: {locations}")
print("\nCalling get_distance_matrix...")
print("-"*60)

try:
    matrix = calc.get_distance_matrix(locations)
    print("-"*60)
    print(f"\n✅ Success! Distance matrix:")
    for i, loc in enumerate(locations):
        print(f"  {loc}: {matrix[i]}")
    print(f"\nGoa -> Mumbai: {matrix[0][1]:.2f} km")
    print(f"Mumbai -> Goa: {matrix[1][0]:.2f} km")
except Exception as e:
    print(f"\n❌ Failed: {e}")
    import traceback
    traceback.print_exc()
