import subprocess
import sys
import os
from pathlib import Path
import shutil

# ------------------------------------------------------------
# Resolve repo root
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parent

# ------------------------------------------------------------
# Locate Julia executable
# ------------------------------------------------------------
JULIA_EXE = shutil.which("julia")
if JULIA_EXE is None:
    print("❌ Julia executable not found in PATH")
    sys.exit(1)

print(f"Using Julia at: {JULIA_EXE}")

# ------------------------------------------------------------
# Generic runner (no shell, no env dependency)
# ------------------------------------------------------------
def run_step(name, command, cwd=None):
    print(f"\n{'=' * 60}")
    print(f"▶ RUNNING: {name}")
    print(f"{'=' * 60}")

    result = subprocess.run(
        command,
        cwd=cwd,
        check=False
    )

    if result.returncode != 0:
        print(f"\n❌ FAILED: {name}")
        sys.exit(result.returncode)

    print(f"✅ COMPLETED: {name}")

# ------------------------------------------------------------
# Main pipeline
# ------------------------------------------------------------
def main():

    # ============================================================
    # STEP 1: Julia physics (v0.1 / v0.2)
    # ============================================================
    run_step(
        name="Julia Core Physics (v0.1 / v0.2)",
        command=[
            JULIA_EXE,
            "Validation/circular_orbit_test.jl",
            str(ROOT),          # <-- REPO_ROOT
            "1",                # ENABLE_NOISE
            "50.0",             # SIGMA_POS (m)
            "0.05"              # SIGMA_VEL (m/s)
        ],
        cwd=ROOT / "core_julia"
    )

    # ============================================================
    # STEP 2: Python visualization
    # ============================================================
    run_step(
        name="Python Visualization",
        command=[
            sys.executable,
            "main.py"
        ],
        cwd=ROOT / "viz_python"
    )

    print("\n🎉 PIPELINE COMPLETED SUCCESSFULLY 🎉")

# ------------------------------------------------------------
if __name__ == "__main__":
    main()
