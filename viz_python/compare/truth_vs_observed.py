import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data_io.load_trajectory import load_trajectory

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "generated"

_, r_t, _ = load_trajectory(DATA / "truth.csv")
_, r_o, _ = load_trajectory(DATA / "observed.csv")

err = np.linalg.norm(r_o - r_t, axis=1)

plt.plot(err)
plt.xlabel("Step")
plt.ylabel("Position Error (m)")
plt.title("Truth vs Observed Error Growth")
plt.grid()
plt.show()
