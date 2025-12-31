from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

from common_io.load_trajectory import load_trajectory
from viz_python.plots.orbit_2d import plot_orbit_2d
from viz_python.plots.orbit_3d import plot_orbit_3d
from viz_python.playback.animate_orbit import animate_orbit

# ============================================================
# Configuration flags (research-friendly)
# ============================================================
ENABLE_ANIMATION = True
ENABLE_OBS_COMPARE = True
ENABLE_SGP4_COMPARE = True

# ============================================================
# Resolve paths
# ============================================================
THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent
DATA = ROOT / "data" / "generated"

# ============================================================
# Load Julia truth
# ============================================================
truth_path = DATA / "truth.csv"
if not truth_path.exists():
    raise FileNotFoundError(f"Missing {truth_path}")

_, r_truth, _ = load_trajectory(truth_path)

# ============================================================
# Basic visualization (v0.1 behavior)
# ============================================================
plot_orbit_2d(r_truth)
plot_orbit_3d(r_truth)

if ENABLE_ANIMATION:
    animate_orbit(r_truth)

# ============================================================
# Truth vs Observed (v0.2)
# ============================================================
obs_path = DATA / "observed.csv"

if ENABLE_OBS_COMPARE and obs_path.exists():
    _, r_obs, _ = load_trajectory(obs_path)

    n = min(len(r_truth), len(r_obs))
    err_obs = np.linalg.norm(r_obs[:n] - r_truth[:n], axis=1)

    plt.figure()
    plt.plot(err_obs)
    plt.xlabel("Step")
    plt.ylabel("Position Error (m)")
    plt.title("Truth vs Observed Error")
    plt.grid(True)
    plt.show()

# ============================================================
# Julia vs CelesTrak SGP4 (v0.3)
# ============================================================
sgp4_path = DATA / "reference_sgp4.csv"

if ENABLE_SGP4_COMPARE and sgp4_path.exists():
    _, r_sgp4, _ = load_trajectory(sgp4_path)

    n = min(len(r_truth), len(r_sgp4))
    err_sgp4 = np.linalg.norm(r_truth[:n] - r_sgp4[:n], axis=1)

    plt.figure()
    plt.plot(err_sgp4)
    plt.xlabel("Step")
    plt.ylabel("Position Difference (m)")
    plt.title("Julia RK4+J2 vs CelesTrak SGP4 (ISS)")
    plt.grid(True)
    plt.show()
