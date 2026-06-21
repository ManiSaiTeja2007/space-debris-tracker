import subprocess
import sys
from pathlib import Path
import shutil
import argparse

# ============================================================
# Resolve repository root
# ============================================================
ROOT = Path(__file__).resolve().parent

# ============================================================
# Build and locate Rust binary robustly
# ============================================================
def build_rust_binary():
    print("\n" + "=" * 60)
    print(">> RUNNING: Cargo Build Physics Engine")
    print("=" * 60)
    cargo_exe = shutil.which("cargo")
    if cargo_exe is None:
        print("[ERROR] cargo executable not found. Make sure Rust is installed.")
        sys.exit(1)
        
    result = subprocess.run([cargo_exe, "build", "--release"], cwd=ROOT / "src" / "physics", check=False)
    if result.returncode != 0:
        print("[ERROR] Cargo build failed.")
        sys.exit(result.returncode)

def get_rust_binary():
    bin_path_win = ROOT / "src" / "physics" / "target" / "release" / "physics_core.exe"
    bin_path_unix = ROOT / "src" / "physics" / "target" / "release" / "physics_core"
    
    if bin_path_win.exists():
        return str(bin_path_win)
    elif bin_path_unix.exists():
        return str(bin_path_unix)
    else:
        # Build first if not found
        build_rust_binary()
        if bin_path_win.exists():
            return str(bin_path_win)
        elif bin_path_unix.exists():
            return str(bin_path_unix)
        else:
            print("[ERROR] Rust binary not found even after building.")
            sys.exit(1)

RSCRIPT_EXE = shutil.which("Rscript")
if RSCRIPT_EXE:
    print(f"Using Rscript at: {RSCRIPT_EXE}")
else:
    print("[WARNING] Rscript not found in PATH. R statistical analysis will be skipped.")

# ============================================================
# Generic step runner (NO shell, deterministic)
# ============================================================
def run_step(name: str, command: list[str], cwd: Path | None = None):
    print(f"\n{'=' * 60}")
    print(f">> RUNNING: {name}")
    print(f"{'=' * 60}")

    result = subprocess.run(command, cwd=cwd, check=False)

    if result.returncode != 0:
        print(f"\n[ERROR] FAILED: {name}")
        sys.exit(result.returncode)

    print(f"[SUCCESS] COMPLETED: {name}")


# ============================================================
# Main orchestration pipeline
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Space Debris Tracker Pipeline")
    parser.add_argument("--dashboard", action="store_true", help="Launch the Standalone Web Dashboard")
    parser.add_argument("--noise", type=int, default=1, choices=[0, 1], help="Enable/disable observation noise (1 or 0)")
    parser.add_argument("--sigma-r", type=float, default=50.0, help="Observation position noise standard deviation (meters)")
    parser.add_argument("--sigma-v", type=float, default=0.05, help="Observation velocity noise standard deviation (m/s)")
    parser.add_argument("--state", type=float, nargs=6, metavar=('PX', 'PY', 'PZ', 'VX', 'VY', 'VZ'),
                        help="Custom initial orbital state vector (6 elements: px py pz vx vy vz)")
    parser.add_argument("--filter", type=str, default="ekf", choices=["ekf", "ukf"], help="Estimation filter type (ekf or ukf)")
    parser.add_argument("--maneuver-time", type=float, default=0.0, help="Time to apply active maneuver (seconds since epoch)")
    parser.add_argument("--maneuver-dv", type=float, nargs=3, default=[0.0, 0.0, 0.0], metavar=('DVR', 'DVT', 'DVN'),
                        help="Impulsive maneuver delta V vector in RTN coordinates (m/s)")
    
    args, unknown = parser.parse_known_args()

    if args.dashboard:
        dashboard_path = ROOT / "src" / "viz" / "dashboard.py"
        print("\n" + "=" * 60)
        print(f">> LAUNCHING STREAMLIT DASHBOARD: {dashboard_path}")
        print("=" * 60)
        
        streamlit_cmd = [sys.executable, "-m", "streamlit", "run", str(dashboard_path)]
        subprocess.run(streamlit_cmd)
        return


    # --------------------------------------------------------
    # STEP 1: Rust physics simulation & Least Squares estimation
    # --------------------------------------------------------
    rust_bin = get_rust_binary()
    rust_cmd = [
        rust_bin,
        str(ROOT),
        str(args.noise),
        str(args.sigma_r),
        str(args.sigma_v),
    ]
    if args.state:
        rust_cmd.extend([str(x) for x in args.state])
    else:
        # Default ISS-like orbit state to pad coordinates before filter/maneuver arguments
        default_state = [6778137.0, 0.0, 0.0, 0.0, 7668.558175407055, 0.0]
        rust_cmd.extend([str(x) for x in default_state])

    rust_cmd.append(args.filter)
    rust_cmd.append(str(args.maneuver_time))
    rust_cmd.append(str(args.maneuver_dv[0]))
    rust_cmd.append(str(args.maneuver_dv[1]))
    rust_cmd.append(str(args.maneuver_dv[2]))

    run_step(
        name="Rust Physics Core & Orbit Determination",
        command=rust_cmd,
        cwd=ROOT,
    )

    # --------------------------------------------------------
    # STEP 2: CelesTrak propagation (SGP4 reference)
    # --------------------------------------------------------
    run_step(
        name="CelesTrak Reference Propagation (SGP4)",
        command=[sys.executable, "-m", "src.catalog.run_celestrak_reference"],
        cwd=ROOT,
    )

    # --------------------------------------------------------
    # STEP 3: Coordinate Conversion Pipeline
    # --------------------------------------------------------
    run_step(
        name="Coordinate Conversion (ECI -> LLA)",
        command=[sys.executable, "-m", "src.coords.run_coordinate_pipeline"],
        cwd=ROOT,
    )

    # --------------------------------------------------------
    # STEP 5: R Statistical Analysis (Optional)
    # --------------------------------------------------------
    if RSCRIPT_EXE:
        run_step(
            name="R Residual & Error Analysis",
            command=[RSCRIPT_EXE, "main.R"],
            cwd=ROOT / "src" / "analysis",
        )

    # --------------------------------------------------------
    # STEP 6: Visualization (Plots & Maps)
    # --------------------------------------------------------
    run_step(
        name="Python Visualization Engine",
        command=[sys.executable, "-m", "src.viz.main"],
        cwd=ROOT,
    )

    print("\n*** PIPELINE COMPLETED SUCCESSFULLY ***")


if __name__ == "__main__":
    main()
