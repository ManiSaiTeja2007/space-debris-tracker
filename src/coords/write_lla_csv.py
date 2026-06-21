from pathlib import Path 
import numpy as np

def write_lla_csv(path: Path, times, lla):
    """
    Write latitude / longitude / altitude trajectory to CSV.

    Parameters
    ----------
    path : Path
        Output CSV file path
    times : iterable
        Time values (seconds)
    lla : iterable
        Iterable of (lat_deg, lon_deg, alt_m)
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="") as f:
        f.write("time,lat,lon,alt\n")
        for t, (lat, lon, alt) in zip(times, lla):
            f.write(f"{t},{lat},{lon},{alt}\n")

