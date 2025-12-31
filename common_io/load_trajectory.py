import numpy as np 
import pandas as pd

def load_trajectory(csv_path):
    df = pd.read_csv(csv_path)

    t = df["time"].values
    r = df[["x", "y", "z"]].values
    v = df[["vx", "vy", "vz"]].values

    return t, r, v

