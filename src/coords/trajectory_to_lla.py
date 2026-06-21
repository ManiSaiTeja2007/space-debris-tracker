from datetime import datetime, timedelta, timezone 
import numpy as np

from src.coords.eci_to_ecef import eci_to_ecef
from src.coords.ecef_to_lla import ecef_to_lla

def trajectory_eci_to_lla(times, r_eci_list, start_utc: datetime):
    lla = []

    for t, r in zip(times, r_eci_list):
        dt = start_utc + timedelta(seconds=float(t))
        r_ecef = eci_to_ecef(r, dt)
        lla.append(ecef_to_lla(r_ecef))

    return np.array(lla)

