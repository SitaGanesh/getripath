import unittest
from app import TSPSolver, DistanceMatrixCalculator

class TestTSPSolver(unittest.TestCase):
    def test_nearest_neighbor_simple(self):
        # 4 locations in a square; symmetric distances
        # indices: 0,1,2,3
        dm = [
            [0, 1, 5, 2],
            [1, 0, 1, 4],
            [5, 1, 0, 1],
            [2, 4, 1, 0]
        ]
        locs = ["A","B","C","D"]
        solver = TSPSolver(locs, dm)
        path, dist = solver.nearest_neighbor(0)
        # Ensure path starts at 0 and returns to 0
        self.assertEqual(path[0], 0)
        self.assertEqual(path[-1], 0)
        self.assertTrue(dist > 0)

class TestDistanceCalculator(unittest.TestCase):
    def test_haversine(self):
        calc = DistanceMatrixCalculator(api_key='')
        # Mumbai (approx) and Delhi (approx)
        mumbai = (19.0760, 72.8777)
        delhi = (28.7041, 77.1025)
        km = calc._haversine_km(mumbai[0], mumbai[1], delhi[0], delhi[1])
        # Rough distance ~1140 km
        self.assertTrue(1000 < km < 1500)

if __name__ == '__main__':
    unittest.main()
