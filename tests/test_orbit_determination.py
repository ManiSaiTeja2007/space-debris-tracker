import subprocess
import shutil
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def build_rust_binary():
    cargo_exe = shutil.which("cargo")
    assert cargo_exe is not None, "cargo executable not found. Make sure Rust is installed."
    
    result = subprocess.run([cargo_exe, "build", "--release"], cwd=ROOT / "src" / "physics", capture_output=True)
    assert result.returncode == 0, f"Cargo build failed: {result.stderr.decode()}"

def get_rust_binary():
    bin_path_win = ROOT / "src" / "physics" / "target" / "release" / "physics_core.exe"
    bin_path_unix = ROOT / "src" / "physics" / "target" / "release" / "physics_core"
    
    if bin_path_win.exists():
        return str(bin_path_win)
    elif bin_path_unix.exists():
        return str(bin_path_unix)
    else:
        build_rust_binary()
        if bin_path_win.exists():
            return str(bin_path_win)
        elif bin_path_unix.exists():
            return str(bin_path_unix)
        else:
            raise FileNotFoundError("Rust binary not found even after compiling.")

def test_rust_orbit_determination():
    # Get Rust binary
    rust_bin = get_rust_binary()

    # Define output files we expect to be generated
    out_dir = ROOT / "data" / "generated"
    metrics_path = out_dir / "estimation_metrics.json"

    # Delete existing metrics file if it exists to ensure we verify the new run
    if metrics_path.exists():
        metrics_path.unlink()

    # Run the Rust simulation & estimation binary
    # Use small noise values to verify accurate convergence
    cmd = [
        rust_bin,
        str(ROOT),
        "1",     # Enable noise
        "10.0",  # Position noise std dev (meters)
        "0.01"   # Velocity noise std dev (m/s)
    ]
    
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, f"Rust binary failed: {result.stderr}\nStdout: {result.stdout}"

    # Verify that metrics file is generated
    assert metrics_path.exists(), "Least Squares estimation metrics were not written."

    # Load metrics
    with metrics_path.open("r") as f:
        metrics = json.load(f)

    # Verify convergence accuracy
    assert metrics["initial_position_error_m"] < 5.0, f"Position estimation error too large: {metrics['initial_position_error_m']} m"
    assert metrics["initial_velocity_error_m_s"] < 0.01, f"Velocity estimation error too large: {metrics['initial_velocity_error_m_s']} m/s"
    
    print("Rust Orbit Determination test passed. Accuracy position error:", metrics["initial_position_error_m"])
