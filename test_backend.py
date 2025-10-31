"""
Test Script for TSP Distance Optimizer Backend
Tests the API endpoints and core functionality
"""

import os
from dotenv import load_dotenv
import requests
import json

# Load .env for local development
load_dotenv()

# Configuration: read backend URL from the environment so CI/Render can override
BASE_URL = os.environ.get('BACKEND_URL', 'http://localhost:5000')
API_URL = f"{BASE_URL}/calculate-route"

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text):
    """Print a formatted header"""
    print(f"\n{BLUE}{'=' * 60}")
    print(f"{text}")
    print(f"{'=' * 60}{RESET}\n")


def print_success(text):
    """Print success message"""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text):
    """Print error message"""
    print(f"{RED}✗ {text}{RESET}")


def print_info(text):
    """Print info message"""
    print(f"{YELLOW}ℹ {text}{RESET}")


def test_health_endpoint():
    """Test the health check endpoint"""
    print_header("Test 1: Health Check Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("Health endpoint is working")
            print_info(f"Response: {response.json()}")
            return True
        else:
            print_error(f"Health endpoint returned status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Health check failed: {str(e)}")
        return False


def test_home_endpoint():
    """Test the home endpoint"""
    print_header("Test 2: Home Endpoint")
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code == 200:
            print_success("Home endpoint is working")
            data = response.json()
            print_info(f"API Version: {data.get('version')}")
            print_info(f"Available endpoints: {len(data.get('endpoints', {}))}")
            return True
        else:
            print_error(f"Home endpoint returned status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Home endpoint test failed: {str(e)}")
        return False


def test_calculate_route_basic():
    """Test basic route calculation"""
    print_header("Test 3: Basic Route Calculation (2 locations)")
    
    test_data = {
        "locations": [
            "Hyderabad, Telangana",
            "Mumbai, Maharashtra"
        ]
    }
    
    try:
        print_info("Sending request with 2 locations...")
        response = requests.post(
            API_URL,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Route calculation successful")
            print_info(f"Locations: {len(data.get('locations', []))}")
            print_info(f"Total Distance: {data.get('total_distance', 0):.2f} km")
            print_info(f"Algorithm Used: {data.get('algorithm_used')}")
            print_info(f"Optimal Path: {' → '.join(data.get('optimal_path', []))}")
            return True
        else:
            print_error(f"Request failed with status: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Route calculation failed: {str(e)}")
        return False


def test_calculate_route_multiple():
    """Test route calculation with multiple locations"""
    print_header("Test 4: Multiple Locations (5 cities)")
    
    test_data = {
        "locations": [
            "Hyderabad, Telangana",
            "Mumbai, Maharashtra",
            "Pune, Maharashtra",
            "Bangalore, Karnataka",
            "Chennai, Tamil Nadu"
        ]
    }
    
    try:
        print_info("Sending request with 5 locations...")
        print_info("This may take 15-30 seconds...")
        
        response = requests.post(
            API_URL,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Route calculation successful")
            print_info(f"Locations: {len(data.get('locations', []))}")
            print_info(f"Total Distance: {data.get('total_distance', 0):.2f} km")
            print_info(f"Algorithm Used: {data.get('algorithm_used')}")
            print_info("Optimal Path:")
            for i, location in enumerate(data.get('optimal_path', []), 1):
                print(f"   {i}. {location}")
            return True
        else:
            print_error(f"Request failed with status: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Route calculation failed: {str(e)}")
        return False


def test_error_handling():
    """Test error handling with invalid data"""
    print_header("Test 5: Error Handling")
    
    # Test with only 1 location (should fail)
    test_data = {
        "locations": ["Hyderabad, Telangana"]
    }
    
    try:
        print_info("Testing with only 1 location (should fail)...")
        response = requests.post(
            API_URL,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 400:
            print_success("Error handling works correctly")
            print_info(f"Error message: {response.json().get('error')}")
            return True
        else:
            print_error("Expected 400 error, but got different response")
            return False
            
    except Exception as e:
        print_error(f"Error handling test failed: {str(e)}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print_header("🧪 TSP Distance Optimizer - Backend Test Suite")
    print_info("Testing backend at: http://localhost:5000")
    
    results = []
    
    # Run all tests
    results.append(("Health Check", test_health_endpoint()))
    results.append(("Home Endpoint", test_home_endpoint()))
    results.append(("Basic Route (2 locations)", test_calculate_route_basic()))
    results.append(("Multiple Locations (5 cities)", test_calculate_route_multiple()))
    results.append(("Error Handling", test_error_handling()))
    
    # Print summary
    print_header("📊 Test Results Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
    
    print(f"\n{BLUE}{'=' * 60}")
    if passed == total:
        print(f"{GREEN}All tests passed! ({passed}/{total}) ✓{RESET}")
    else:
        print(f"{YELLOW}Some tests failed: {passed}/{total} passed{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{RESET}")
        exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        exit(1)
