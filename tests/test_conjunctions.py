import json
from pathlib import Path
import subprocess
import shutil

ROOT = Path(__file__).resolve().parents[1]

def test_rust_conjunction_analysis():
    # Make sure Rust binary exists
    bin_path_win = ROOT / "src" / "physics" / "target" / "release" / "physics_core.exe"
    bin_path_unix = ROOT / "src" / "physics" / "target" / "release" / "physics_core"
    rust_bin = str(bin_path_win) if bin_path_win.exists() else str(bin_path_unix)

    # If it doesn't exist, build it
    if not Path(rust_bin).exists():
        cargo_exe = shutil.which("cargo")
        assert cargo_exe is not None, "cargo not found"
        subprocess.run([cargo_exe, "build", "--release"], cwd=ROOT / "src" / "physics", check=True)

    # Clean the conjunctions output file if it exists to ensure a fresh test
    conj_path = ROOT / "data" / "generated" / "conjunctions.json"
    if conj_path.exists():
        conj_path.unlink()

    # Run the Rust binary
    cmd = [
        rust_bin,
        str(ROOT),
        "1",     # Enable noise
        "50.0",  # Position noise std dev (meters)
        "0.05"   # Velocity noise std dev (m/s)
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, f"Rust binary execution failed: {result.stderr}"

    # Verify that conjunctions.json is generated
    assert conj_path.exists(), "conjunctions.json was not written by the Rust engine."

    # Load conjunctions
    with conj_path.open("r") as f:
        conjs = json.load(f)

    # Verify formatting and content
    assert isinstance(conjs, list), "Conjunctions JSON should contain a list."
    
    # We should have found some conjunctions (our active TLE database contains ~15k entries)
    assert len(conjs) > 0, "No conjunctions detected inside the threshold."

    # Verify fields of the first conjunction
    first = conjs[0]
    required_fields = [
        "sat_name", "sat_id", "min_distance_m", "tca_seconds",
        "tca_utc", "relative_position_m", "relative_velocity_m_s",
        "sat_position_m", "sat_velocity_m_s"
    ]
    for field in required_fields:
        assert field in first, f"Missing field '{field}' in conjunction result."

    print(f"Rust conjunction screening test passed. Total conjunctions found: {len(conjs)}")
