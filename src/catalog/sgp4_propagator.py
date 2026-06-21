from sgp4.api import Satrec, jday 
from datetime import datetime
import numpy as np

def propagate_tle(line1: str, line2: str, epoch_utc: datetime):
    """
    Propagate a single TLE to a given UTC epoch using SGP4.
    Returns ECI position/velocity in meters and m/s.
    """
    sat = Satrec.twoline2rv(line1, line2)

    jd, fr = jday(
        epoch_utc.year, epoch_utc.month, epoch_utc.day,
        epoch_utc.hour, epoch_utc.minute,
        epoch_utc.second + epoch_utc.microsecond * 1e-6
    )

    err, r_km, v_km_s = sat.sgp4(jd, fr)
    if err != 0:
        raise RuntimeError(f"SGP4 error code {err}")

    # km → m
    r_m = np.array(r_km) * 1000.0
    v_m = np.array(v_km_s) * 1000.0
    return r_m, v_m

