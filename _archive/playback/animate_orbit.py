import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

def animate_orbit(r, interval=30):
    fig, ax = plt.subplots(figsize=(6,6))
    ax.set_aspect("equal")

    line, = ax.plot([], [], lw=2)
    point, = ax.plot([], [], "ro")

    lim = np.max(np.abs(r)) * 1.1
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)

    def update(i):
        line.set_data(r[:i,0], r[:i,1])
        point.set_data([r[i,0]], [r[i,1]])
        return line, point

    ani = FuncAnimation(fig, update, frames=len(r), interval=interval)
    plt.show()
