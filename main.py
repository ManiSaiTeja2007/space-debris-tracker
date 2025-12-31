import subprocess 
import sys
from pathlib import Path
import shutil

# ============================================================
# Resolve repository root
# ============================================================
ROOT = Path(__file__).resolve().parent

# ============================================================
# Locate Julia executable robustly
# ============================================================
JULIA_EXE = shutil.which("julia")
if JULIA_EXE is None:
    print("❌ Julia executable not found in PATH")
    sys.exit(1)

print(f"Using Julia at: {JULIA_EXE}")


# ============================================================
# Generic step runner (NO shell, deterministic)
# ============================================================
def run_step(name: str, command: list[str], cwd: Path | None = None):
    print(f"\n{'=' * 60}")
    print(f"▶ RUNNING: {name}")
    print(f"{'=' * 60}")

    result = subprocess.run(command, cwd=cwd, check=False)

    if result.returncode != 0:
        print(f"\n❌ FAILED: {name}")
        sys.exit(result.returncode)

    print(f"✅ COMPLETED: {name}")


# ============================================================
# Main orchestration pipeline
# ============================================================
def main():

    # --------------------------------------------------------
    # STEP 1: Julia physics (truth + optional noise)
    # --------------------------------------------------------
    # Arguments:
    #   ARGS[1] = repo_root
    #   ARGS[2] = enable_noise (1 / 0)
    #   ARGS[3] = sigma_position (m)
    #   ARGS[4] = sigma_velocity (m/s)
    #
    run_step(
        name="Julia Core Physics (v0.1 / v0.2)",
        command=[
            JULIA_EXE,
            "Validation/circular_orbit_test.jl",
            str(ROOT),  # repo root (authoritative)
            "1",  # ENABLE_NOISE (set "0" for v0.1)
            "50.0",  # SIGMA_POS (meters)
            "0.05",  # SIGMA_VEL (m/s)
        ],
        cwd=ROOT / "core_julia",
    )

    # --------------------------------------------------------
    # STEP 2: CelesTrak reference propagation (SGP4)
    # --------------------------------------------------------
    # Produces:
    #   data/generated/reference_sgp4.csv
    #
    run_step(
        name="CelesTrak SGP4 Reference (ISS)",
        command=[sys.executable, "-m", "catalog.run_celestrak_reference"],
        cwd=ROOT,
    )

    # --------------------------------------------------------
    # STEP 3: Visualization (Julia truth + optional comparisons)
    # --------------------------------------------------------
    # This step:
    #   - Always visualizes Julia truth
    #   - Optionally compares truth vs observed
    #   - Optionally compares truth vs SGP4 reference
    #
    run_step(
        name="Python Visualization",
        command=[sys.executable, "-m", "viz_python.main"],
        cwd=ROOT,
    )

    # --------------------------------------------------------
    print("\n🎉 PIPELINE COMPLETED SUCCESSFULLY 🎉")


# ============================================================
if __name__ == "__main__":
    main()

