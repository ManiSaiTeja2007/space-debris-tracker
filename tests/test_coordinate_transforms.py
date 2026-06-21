from datetime import datetime, timezone
import numpy as np
from src.coords.time import julian_date, gmst
from src.coords.eci_to_ecef import eci_to_ecef
from src.coords.ecef_to_lla import ecef_to_lla

def test_julian_date():
    # J2000.0 epoch: 2000-01-01 12:00:00 UTC is exactly JD 2451545.0
    dt = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    jd = julian_date(dt)
    assert abs(jd - 2451545.0) < 1e-6

def test_coordinate_roundtrip():
    # Take a point in ECI
    r_eci = np.array([6378137.0 + 400000.0, 0.0, 0.0]) # 400km altitude on equator
    dt = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    # ECI -> ECEF
    r_ecef = eci_to_ecef(r_eci, dt)
    assert r_ecef.shape == (3,)
    # Magnitude should be preserved (pure rotation)
    assert abs(np.linalg.norm(r_ecef) - np.linalg.norm(r_eci)) < 1e-3
    
    # ECEF -> LLA
    lat, lon, alt = ecef_to_lla(r_ecef)
    
    # Equatorial point should have latitude ~0
    assert abs(lat) < 1e-5
    # Altitude should be ~400,000 meters
    assert abs(alt - 400000.0) < 1e-3
