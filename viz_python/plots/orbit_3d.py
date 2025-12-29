import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from .earth import earth_sphere

def plot_orbit_3d(r):
    fig = plt.figure(figsize=(8,8))
    ax = fig.add_subplot(111, projection="3d")

    ax.plot(r[:,0], r[:,1], r[:,2], label="Orbit")

    xe, ye, ze = earth_sphere()
    ax.plot_surface(xe, ye, ze, color="blue", alpha=0.3)

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m)")
    ax.set_title("3D Orbit (ECI)")
    ax.legend()

    plt.show()
