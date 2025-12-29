import numpy as np

def earth_sphere(radius=6378137.0, n=50):
    u = np.linspace(0, 2*np.pi, n)
    v = np.linspace(0, np.pi, n)

    x = radius * np.outer(np.cos(u), np.sin(v))
    y = radius * np.outer(np.sin(u), np.sin(v))
    z = radius * np.outer(np.ones_like(u), np.cos(v))

    return x, y, z
