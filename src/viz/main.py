"""
src/viz/main.py

PURPOSE:
--------
Orchestrate all visual plots (2D orbit, 3D orbit comparisons, and 3D conjunction plots).
Saves figures to data/generated/ and displays them.
"""

from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt

from src.io_utils.load_trajectory import load_trajectory
from src.viz.plots.orbit_2d import plot_orbit_2d
from src.viz.plots.orbit_3d import plot_orbit_3d
from src.viz.plots.conjunction_viz import plot_conjunctions_3d

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "generated"

def main():
    print("\n" + "=" * 60)
    print(">> RUNNING: Python Plotting & Visualization")
    print("=" * 60)

    truth_path = DATA_DIR / "truth.csv"
    observed_path = DATA_DIR / "observed.csv"
    estimated_path = DATA_DIR / "estimated.csv"
    conjunctions_path = DATA_DIR / "conjunctions.json"

    if not truth_path.exists():
        raise FileNotFoundError(f"Missing truth trajectory file: {truth_path}")

    # 1. Load Trajectories
    _, r_truth, _ = load_trajectory(truth_path)
    r_observed = None
    r_estimated = None

    if observed_path.exists():
        _, r_observed, _ = load_trajectory(observed_path)
    if estimated_path.exists():
        _, r_estimated, _ = load_trajectory(estimated_path)

    # 2. Plot 2D Comparison Orbit
    fig_2d, ax_2d = plt.subplots(figsize=(8, 8))
    ax_2d.plot(r_truth[:, 0], r_truth[:, 1], 'g-', label="Ground Truth", alpha=0.8, lw=2)
    if r_observed is not None:
        ax_2d.scatter(r_observed[::5, 0], r_observed[::5, 1], color="red", s=10, label="Observed (Noisy, sampled)", alpha=0.5)
    if r_estimated is not None:
        ax_2d.plot(r_estimated[:, 0], r_estimated[:, 1], 'c--', label="Estimated (Tracked)", alpha=0.9, lw=2)
    
    ax_2d.scatter(0, 0, color="blue", s=100, label="Earth Core")
    ax_2d.set_aspect("equal")
    ax_2d.set_xlabel("X (m)")
    ax_2d.set_ylabel("Y (m)")
    ax_2d.set_title("2D Orbit Trajectory comparison (ECI)")
    ax_2d.legend()
    ax_2d.grid(True)
    
    plot_2d_out = DATA_DIR / "orbit_comparison_2d.png"
    fig_2d.savefig(plot_2d_out, dpi=150)
    print(f"Saved 2D comparison plot to: {plot_2d_out}")

    # 3. Plot 3D Comparison Orbit
    fig_3d = plt.figure(figsize=(10, 10))
    ax_3d = fig_3d.add_subplot(111, projection="3d")
    ax_3d.plot(r_truth[:, 0], r_truth[:, 1], r_truth[:, 2], 'g-', label="Ground Truth", lw=2)
    if r_estimated is not None:
        ax_3d.plot(r_estimated[:, 0], r_estimated[:, 1], r_estimated[:, 2], 'c--', label="Estimated (Tracked)", lw=2)
    
    # Plot Earth Sphere
    from src.viz.plots.earth import earth_sphere
    xe, ye, ze = earth_sphere()
    ax_3d.plot_surface(xe, ye, ze, color="blue", alpha=0.1)
    
    ax_3d.set_xlabel("X (m)")
    ax_3d.set_ylabel("Y (m)")
    ax_3d.set_zlabel("Z (m)")
    ax_3d.set_title("3D Orbit Trajectory comparison (ECI)")
    ax_3d.legend()
    
    max_range = np.max(np.abs(r_truth)) * 1.1
    ax_3d.set_xlim(-max_range, max_range)
    ax_3d.set_ylim(-max_range, max_range)
    ax_3d.set_zlim(-max_range, max_range)

    plot_3d_out = DATA_DIR / "orbit_comparison_3d.png"
    fig_3d.savefig(plot_3d_out, dpi=150)
    print(f"Saved 3D comparison plot to: {plot_3d_out}")

    # 4. Plot Conjunctions (if available)
    if conjunctions_path.exists() and r_estimated is not None:
        with conjunctions_path.open("r") as f:
            conjs = json.load(f)
        if len(conjs) > 0:
            fig_conj = plot_conjunctions_3d(r_estimated, conjs)
            plot_conj_out = DATA_DIR / "conjunction_map_3d.png"
            fig_conj.savefig(plot_conj_out, dpi=150)
            print(f"Saved 3D conjunction map to: {plot_conj_out}")
        else:
            print("No conjunctions found within warning threshold to plot.")
    else:
        print("Skipping conjunction plot (conjunctions.json or estimated.csv missing).")

    print("All plots generated and saved successfully.")
    print("[SUCCESS] COMPLETED: Python Plotting & Visualization")

if __name__ == "__main__":
    main()
