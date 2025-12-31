import numpy as np 
from datetime import datetime, timezone

def julian_date(dt: datetime) -> float:
    if dt.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware (UTC)")

    year = dt.year
    month = dt.month
    day = dt.day + (
        dt.hour + (dt.minute + dt.second / 60.0) / 60.0
    ) / 24.0

    if month <= 2:
        year -= 1
        month += 12

    A = year // 100
    B = 2 - A + A // 4

    jd = int(365.25 * (year + 4716)) \
       + int(30.6001 * (month + 1)) \
       + day + B - 1524.5

    return jd


def gmst(dt: datetime) -> float:
    jd = julian_date(dt)
    T = (jd - 2451545.0) / 36525.0

    gmst_sec = (
        67310.54841
        + (876600.0 * 3600 + 8640184.812866) * T
        + 0.093104 * T**2
        - 6.2e-6 * T**3
    )

    gmst_rad = np.deg2rad((gmst_sec / 240.0) % 360.0)
    return gmst_rad

