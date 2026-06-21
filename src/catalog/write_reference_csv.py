from pathlib import Path 

def write_csv(path: Path, times, rs, vs):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        f.write("time,x,y,z,vx,vy,vz\n")
        for t, r, v in zip(times, rs, vs):
            f.write(
                f"{t},{r[0]},{r[1]},{r[2]},{v[0]},{v[1]},{v[2]}\n"
            )

