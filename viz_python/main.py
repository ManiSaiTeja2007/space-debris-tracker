"""
viz_python/main.py

PURPOSE:
--------
Geometric visualization ONLY.

This module is used to visually sanity-check orbit geometry
(e.g., shape, orientation, continuity).

IMPORTANT:
----------
- No statistics are computed here.
- No residuals are analyzed here.
- No comparisons are performed here.
- All statistical analysis is handled exclusively in analysis_r/.
"""

from pathlib import Path

import matplotlib.pyplot as plt

from common_io.load_trajectory import load_trajectory
from viz_python.plots.orbit_2d import plot_orbit_2d
from viz_python.plots.orbit_3d import plot_orbit_3d


# ------------------------------------------------------------
# Resolve paths
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "generated"


def main():
    """
    Load truth trajectory and perform basic geometric visualization.
    """

    truth_path = DATA_DIR / "truth.csv"

    if not truth_path.exists():
        raise FileNotFoundError(f"Missing trajectory file: {truth_path}")

    # Load trajectory (ECI coordinates)
    _, r, _ = load_trajectory(truth_path)

    # 2D sanity plot
    plot_orbit_2d(r)

    # 3D sanity plot
    plot_orbit_3d(r)

    plt.show()


if __name__ == "__main__":
    main()
