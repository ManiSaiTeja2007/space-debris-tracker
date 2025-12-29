from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

from data_io.load_trajectory import load_trajectory
from plots.orbit_2d import plot_orbit_2d
from plots.orbit_3d import plot_orbit_3d
from playback.animate_orbit import animate_orbit

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "generated"

truth_path = DATA / "truth.csv"
obs_path = DATA / "observed.csv"

# ------------------------------------------------------------
# Always visualize truth
# ------------------------------------------------------------
_, r_truth, _ = load_trajectory(truth_path)

plot_orbit_2d(r_truth)
plot_orbit_3d(r_truth)
animate_orbit(r_truth)

# ------------------------------------------------------------
# If observed exists, compare
# ------------------------------------------------------------
if obs_path.exists():
    _, r_obs, _ = load_trajectory(obs_path)
    err = np.linalg.norm(r_obs - r_truth, axis=1)

    plt.figure()
    plt.plot(err)
    plt.xlabel("Step")
    plt.ylabel("Position Error (m)")
    plt.title("Truth vs Observed Error")
    plt.grid()
    plt.show()
