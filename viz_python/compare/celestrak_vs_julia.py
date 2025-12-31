import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from common_io.load_trajectory import load_trajectory

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "generated"

_, r_j, _ = load_trajectory(DATA / "truth.csv")
_, r_s, _ = load_trajectory(DATA / "reference_sgp4.csv")

n = min(len(r_j), len(r_s))
err = np.linalg.norm(r_j[:n] - r_s[:n], axis=1)

plt.plot(err)
plt.xlabel("Step")
plt.ylabel("Position difference (m)")
plt.title("Julia RK4+J2 vs CelesTrak SGP4 (ISS)")
plt.grid(True)
plt.show()
