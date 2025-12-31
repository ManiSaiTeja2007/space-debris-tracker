import numpy as np 
from datetime import datetime
from coords.time import gmst

def eci_to_ecef(r_eci: np.ndarray, dt: datetime) -> np.ndarray:
    theta = gmst(dt)

    R = np.array([
        [ np.cos(theta),  np.sin(theta), 0],
        [-np.sin(theta),  np.cos(theta), 0],
        [ 0,              0,             1]
    ])

    return R @ r_eci

