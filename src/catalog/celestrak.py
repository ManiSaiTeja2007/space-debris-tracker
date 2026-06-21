from pathlib import Path
import requests
import numpy as np

CELESTRAK_ACTIVE = (
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
)

def generate_synthetic_tles(count=500):
    """
    Generate a database of 500 synthetic objects in LEO near the ISS orbit.
    Acts as a self-contained fallback for offline testing.
    """
    lines = []
    np.random.seed(42)
    
    for i in range(1, count + 1):
        sat_num = 90000 + i
        name = f"SYNTHETIC_DEBRIS_{i:03d}"
        
        inc = np.random.uniform(0.0, 180.0)
        raan = np.random.uniform(0.0, 360.0)
        ecc = np.random.uniform(0.0, 0.02)
        argp = np.random.uniform(0.0, 360.0)
        ma = np.random.uniform(0.0, 360.0)
        mm = np.random.uniform(14.0, 16.5) # revs per day
        
        # Line 1 placeholder
        l1 = f"1 {sat_num:05d}U 24001A   24001.00000000  .00000100  00000+0  10000-3 0  9999"
        
        # Line 2 placeholder
        ecc_int = int(round(ecc * 1e7))
        l2 = f"2 {sat_num:05d} {inc:8.4f} {raan:8.4f} {ecc_int:07d} {argp:8.4f} {ma:8.4f} {mm:11.8f}    0"
        
        # Checksum calculator
        def compute_checksum(line):
            s = 0
            for char in line[:68]:
                if char.isdigit():
                    s += int(char)
                elif char == '-':
                    s += 1
            return s % 10
            
        l1 = l1 + str(compute_checksum(l1))
        l2 = l2 + str(compute_checksum(l2))
        
        lines.append(name)
        lines.append(l1)
        lines.append(l2)
        
    return "\n".join(lines)


def fetch_active_tles(cache_dir: Path) -> Path:
    """
    Download Active Satellites TLEs from CelesTrak.
    Cached locally to be polite and reproducible.
    Falls back to generating synthetic TLE database if offline.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    tle_path = cache_dir / "active.tle"

    if tle_path.exists():
        return tle_path

    try:
        print(f"Fetching active TLEs from CelesTrak...")
        r = requests.get(CELESTRAK_ACTIVE, timeout=10)
        r.raise_for_status()
        tle_path.write_text(r.text)
        print(f"Successfully fetched online TLEs to {tle_path}")
    except Exception as e:
        print(f"[WARNING] Could not connect to CelesTrak ({e}).")
        print(f"Generating synthetic TLE database of 500 debris/satellites for offline mode...")
        synthetic_data = generate_synthetic_tles(500)
        tle_path.write_text(synthetic_data)
        print(f"Synthetic catalog written to {tle_path}")

    return tle_path
