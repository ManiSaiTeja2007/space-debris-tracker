import numpy as np 

# WGS-84 constants
a = 6378137.0
f = 1 / 298.257223563
e2 = f * (2 - f)

def ecef_to_lla(r: np.ndarray):
    x, y, z = r
    lon = np.arctan2(y, x)

    p = np.sqrt(x**2 + y**2)
    lat = np.arctan2(z, p * (1 - e2))

    for _ in range(5):
        N = a / np.sqrt(1 - e2 * np.sin(lat)**2)
        alt = p / np.cos(lat) - N
        lat = np.arctan2(z, p * (1 - e2 * (N / (N + alt))))

    return (
        np.degrees(lat),
        np.degrees(lon),
        alt
    )

