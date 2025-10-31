import requests
import json
import sys

BACKEND = 'http://localhost:5000'

LOCATIONS = [
    "Trimbakeshwar Temple, Trimbak, Maharashtra, India",
    "Kholapuri, Maharashtra, India",
    "Shingapura, Karnataka, India",
    "Bhimashankar Temple, Bhimashankar, Maharashtra, India",
    "Asif Nagar mandal, Telangana, India",
    "Ganagapura Dattatreya Temple, Tellura, Karnataka, India",
    "TULJA BHAVANI MATA TEMPLE, Pohara, Maharashtra, India",
    "Vitthal Rukmini Temple, Pandharpur, Maharashtra, India",
    "Yellamma Temple, Chitradurga, Karnataka, India",
    "Shirdi Sai Baba Temple, Karnataka, India",
    "Jyotiba Temple, Panhala, Maharashtra, India",
]


def pretty_print(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def check_autocomplete(loc):
    try:
        q = loc.split(',')[0]
        r = requests.get(f"{BACKEND}/autocomplete", params={"q": q, "limit": 6}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def run_test():
    print('Posting locations to /calculate-route')
    try:
        r = requests.post(f"{BACKEND}/calculate-route", json={"locations": LOCATIONS}, timeout=120)
    except Exception as e:
        print('Request to backend failed:', e)
        print('Make sure the backend is running (python app.py) and accessible at', BACKEND)
        sys.exit(2)

    if r.status_code != 200:
        print('Backend returned status', r.status_code)
        try:
            pretty_print(r.json())
        except Exception:
            print(r.text[:1000])
        sys.exit(1)

    data = r.json()
    print('\n=== Response summary ===')
    print('Total distance:', data.get('total_distance'))
    print('Algorithm used:', data.get('algorithm_used'))
    print('Locations count:', len(data.get('locations', [])))

    matrix = data.get('distance_matrix')
    if not matrix:
        print('No distance matrix returned')
        pretty_print(data)
        return

    n = len(matrix)
    sentinel = 999999.0
    sentinel_pairs = []
    for i in range(n):
        for j in range(n):
            v = matrix[i][j]
            if isinstance(v, (int, float)) and v >= sentinel:
                sentinel_pairs.append((i, j, data['locations'][i], data['locations'][j]))

    print('\nDistance matrix size:', n)
    print('Sentinel (unreachable) pairs count:', len(sentinel_pairs))
    if sentinel_pairs:
        print('\nSample sentinel pairs (first 20):')
        for t in sentinel_pairs[:20]:
            print(f"  [{t[0]}]->[{t[1]}] {t[2]} -> {t[3]}")

    # Check autocomplete suggestions for each location prefix
    print('\n=== Autocomplete diagnostics ===')
    for loc in LOCATIONS:
        print('\nQuery:', loc)
        ac = check_autocomplete(loc)
        pretty_print(ac)

    print('\nDone')


if __name__ == '__main__':
    run_test()
