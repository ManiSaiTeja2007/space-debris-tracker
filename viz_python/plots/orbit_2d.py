import matplotlib.pyplot as plt
from .earth import earth_sphere
import numpy as np

def plot_orbit_2d(r):
    fig, ax = plt.subplots(figsize=(6,6))

    ax.plot(r[:,0], r[:,1], label="Orbit")
    ax.scatter(0, 0, color="blue", label="Earth")

    ax.set_aspect("equal")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title("2D Orbit Projection (ECI)")
    ax.legend()
    ax.grid(True)

    plt.show()
