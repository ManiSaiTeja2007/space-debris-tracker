# 🛰️ Space Debris Tracker

A high-fidelity, multi-language astrodynamics simulation and space object tracking system. It combines a **Rust-powered physics engine**, **Python orchestration**, an **R statistical analysis layer**, and a **Streamlit interactive dashboard** into a single end-to-end pipeline — from orbit simulation to real-time conjunction (collision risk) screening.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Feature Summary](#feature-summary)
4. [Technology Stack](#technology-stack)
5. [Project Structure](#project-structure)
6. [Prerequisites](#prerequisites)
7. [Installation](#installation)
8. [Configuration — time_reference.json](#configuration--time_referencejson)
9. [Running the Pipeline](#running-the-pipeline)
10. [CLI Arguments Reference](#cli-arguments-reference)
11. [Module Reference](#module-reference)
12. [Generated Outputs](#generated-outputs)
13. [Interactive Dashboard](#interactive-dashboard)
14. [Testing](#testing)
15. [Offline Mode](#offline-mode)

---

## Overview

Space Debris Tracker simulates the full orbit-determination and conjunction-screening workflow used in real space-surveillance operations:

1. **Simulate** a true satellite trajectory with realistic high-fidelity perturbation forces.
2. **Corrupt** the trajectory with configurable Gaussian observation noise.
3. **Recover** the true orbit using Batch Least Squares and a Kalman Filter (EKF or UKF).
4. **Screen** the estimated trajectory against every catalogued satellite in the CelesTrak active TLE database, computing a **probability of collision** (Foster's method) for every close approach.
5. **Analyse** residuals and tracking accuracy with R.
6. **Visualise** everything through static plots and a live Streamlit dashboard.

---

## Architecture

```
+----------------------------------------------------------+
|                       main.py                            |
|          Python Pipeline Orchestrator                    |
+------+---------------+--------------+-----------+--------+
       |               |              |           |
       v               v              v           v
 +----------+  +-------------+  +---------+  +----------+
 |  Rust    |  |  Python     |  |   R     |  |  Python  |
 | Physics  |  |  Catalog +  |  | Stats   |  |  Viz +   |
 |  Core    |  |  Coord Conv |  | Analysis|  |Dashboard |
 +----+-----+  +------+------+  +----+----+  +----+-----+
      |               |              |             |
      v               v              v             v
 data/generated/  (LLA CSVs)  statistics.json  plots + dashboard
 truth.csv
 observed.csv
 estimated.csv
 ekf.csv
 conjunctions.json
 estimation_metrics.json
```

**Data flows through a single shared directory: `data/generated/`.** Every stage reads from and writes to this location, with `time_reference.json` acting as the global time contract shared across all languages.

---

## Feature Summary

| Feature | Detail |
|---|---|
| **Orbit Propagator** | RK4 numerical integrator with J2/J3/J4 zonal harmonics, atmospheric drag (exponential density), solar radiation pressure (cylindrical shadow), and Sun/Moon third-body gravity |
| **Orbit Determination** | Batch Least Squares via iterative normal equations (LU decomposition) |
| **State Estimation** | Extended Kalman Filter (EKF) with numerical STM; Unscented Kalman Filter (UKF) with sigma-point propagation |
| **Conjunction Screening** | Parallel screening of the full CelesTrak catalog using Rayon; Foster's 2D Pc computed in the B-plane encounter frame |
| **SGP4 Reference** | ISS-TLE-based SGP4 reference trajectory for comparison |
| **Coordinate Conversion** | ECI -> ECEF -> LLA (latitude / longitude / altitude) pipeline with GMST rotation |
| **Statistical Analysis** | R-computed RMSE, mean error, max error, and standard deviation for observation and tracking residuals |
| **Visualisation** | 2D/3D orbit comparison plots, 3D conjunction proximity map, Streamlit web dashboard |
| **Maneuver Simulation** | Impulsive dV applied at user-specified time in RTN frame |
| **Offline Fallback** | Auto-generates 500 synthetic LEO TLEs when CelesTrak is unreachable |

---

## Technology Stack

| Layer | Language / Tool | Version |
|---|---|---|
| Physics Engine | **Rust** | 2021 edition |
| Linear Algebra | `nalgebra` | 0.32 |
| SGP4 (Rust) | `sgp4` crate | 2.4 |
| Parallelism | `rayon` | 1.8 |
| Serialisation | `serde` / `serde_json` | 1.0 |
| Pipeline Orchestration | **Python** | 3.10+ |
| TLE Fetching / SGP4 (Py) | `sgp4` | - |
| Dashboard | `streamlit` | - |
| Interactive Plots | `plotly` | - |
| Static Plots | `matplotlib` | - |
| Data Wrangling | `numpy`, `pandas` | - |
| HTTP | `requests` | - |
| Statistical Analysis | **R** / `Rscript` | optional |

---

## Project Structure

```
space-debris-tracker/
|
+-- main.py                     # Top-level pipeline orchestrator & CLI entry point
+-- requirements.txt            # Python dependencies
+-- time_reference.json         # Global time contract (epoch, step size, steps)
|
+-- src/
|   +-- physics/                # Rust astrodynamics engine (Cargo package: physics_core)
|   |   +-- Cargo.toml
|   |   +-- src/
|   |       +-- main.rs         # Entry point: simulation -> estimation -> screening
|   |       +-- constants.rs    # Physical constants (mu, Re, J2-J4, Cd, SRP...)
|   |       +-- state.rs        # OrbitalState struct (position + velocity vectors)
|   |       +-- dynamics.rs     # State derivative (sum of all accelerations)
|   |       +-- gravity.rs      # Point-mass gravity
|   |       +-- j2.rs           # J2, J3, J4 zonal harmonic perturbations
|   |       +-- drag.rs         # Exponential atmospheric drag model
|   |       +-- srp.rs          # Solar Radiation Pressure + cylindrical shadow
|   |       +-- third_body.rs   # Sun & Moon third-body gravitational acceleration
|   |       +-- rk4.rs          # 4th-order Runge-Kutta integrator
|   |       +-- propagator.rs   # Multi-step trajectory propagation (with covariance)
|   |       +-- noise.rs        # Gaussian observation noise injection
|   |       +-- estimation.rs   # Batch Least Squares + Extended Kalman Filter (EKF)
|   |       +-- ukf.rs          # Unscented Kalman Filter (UKF)
|   |       +-- conjunction.rs  # Parallel conjunction screening + Foster Pc
|   |
|   +-- catalog/                # TLE fetching & SGP4 reference propagation (Python)
|   |   +-- celestrak.py        # CelesTrak TLE downloader + synthetic fallback generator
|   |   +-- catalog_reader.py   # TLE file parser helpers
|   |   +-- selectors.py        # Satellite selector utilities
|   |   +-- sgp4_propagator.py  # SGP4 wrapper
|   |   +-- run_celestrak_reference.py  # Step 2: generate reference_sgp4.csv
|   |   +-- write_reference_csv.py
|   |
|   +-- coords/                 # Coordinate conversion pipeline (Python)
|   |   +-- __init__.py
|   |   +-- time.py             # GMST calculation
|   |   +-- eci_to_ecef.py      # ECI -> ECEF rotation
|   |   +-- ecef_to_lla.py      # ECEF -> Geodetic (lat/lon/alt) via WGS-84
|   |   +-- trajectory_to_lla.py# Full ECI trajectory -> LLA array
|   |   +-- write_lla_csv.py    # Write LLA CSV files
|   |   +-- run_coordinate_pipeline.py  # Step 3: process all ECI CSVs -> LLA
|   |
|   +-- io_utils/               # Shared I/O utilities (Python)
|   |   +-- __init__.py
|   |   +-- load_trajectory.py  # Load ECI CSV -> numpy arrays; write trajectory CSV
|   |   +-- write_residuals.py  # Write residual arrays to CSV
|   |
|   +-- analysis/               # R statistical analysis (optional)
|   |   +-- main.R              # Orchestrator: loads CSVs, computes residuals/metrics
|   |   +-- io/                 # R I/O helpers (load_trajectory.R)
|   |   +-- residuals/          # compute_residuals.R
|   |   +-- statistics/         # compute_metrics.R (RMSE, max, mean, SD)
|   |
|   +-- viz/                    # Visualisation (Python)
|       +-- __init__.py
|       +-- main.py             # Step 4: generate all static matplotlib plots
|       +-- dashboard.py        # Streamlit interactive web dashboard
|       +-- plots/
|           +-- orbit_2d.py     # 2D XY-plane orbit plotter
|           +-- orbit_3d.py     # 3D matplotlib orbit plotter
|           +-- earth.py        # Earth sphere mesh generator
|           +-- conjunction_viz.py  # 3D conjunction proximity mapper
|
+-- data/
|   +-- cache/                  # Cached TLE files (active.tle)
|   +-- catalogs/               # Additional satellite catalog files
|   +-- generated/              # All pipeline output files (CSVs, JSONs, PNGs)
|
+-- tests/
|   +-- test_conjunctions.py        # Validates Rust conjunction output
|   +-- test_orbit_determination.py # Validates EKF/LS convergence accuracy
|   +-- test_coordinate_transforms.py # Validates ECI->LLA pipeline
|
+-- bat/
    +-- githubPushOrigin.bat    # Helper script for pushing to GitHub
```

---

## Prerequisites

| Tool | Required | Notes |
|---|---|---|
| Python 3.10+ | Yes | With `pip` |
| Rust + Cargo | Yes | Install from https://rustup.rs/ |
| R + Rscript | Optional | Statistical analysis step is skipped if absent |
| Internet access | Optional | Falls back to synthetic TLE database if offline |

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/ManiSaiTeja2007/space-debris-tracker.git
cd space-debris-tracker

# 2. Create and activate a Python virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Build the Rust physics engine
#    (main.py will do this automatically on first run, but you can pre-build)
cd src/physics
cargo build --release
cd ../..
```

---

## Configuration — `time_reference.json`

The **global time contract** shared by all pipeline stages. Every module reads this file — none of them define time independently.

```json
{
  "epoch_utc": "2024-01-01T00:00:00Z",
  "dt_seconds": 10,
  "steps": 540
}
```

| Field | Description | Default |
|---|---|---|
| `epoch_utc` | Simulation start time (ISO 8601, UTC) | `2024-01-01T00:00:00Z` |
| `dt_seconds` | Integration time step in seconds | `10` |
| `steps` | Number of time steps | `540` (90 min at 10 s/step = one full orbit) |

> **Total simulation duration** = `dt_seconds x steps`. With the defaults, this covers exactly one ISS orbital period.

---

## Running the Pipeline

### Full Pipeline (default ISS-like orbit, EKF, noise enabled)

```bash
python main.py
```

### Custom orbit + UKF filter

```bash
python main.py --filter ukf --state 6778137.0 0.0 0.0 0.0 7668.56 0.0
```

### Simulate with an impulsive maneuver

```bash
python main.py --maneuver-time 2700.0 --maneuver-dv 0 10 0
```

This applies a 10 m/s prograde (T-axis) burn at 2700 seconds into the simulation.

### Disable observation noise (perfect observations)

```bash
python main.py --noise 0
```

### Launch the interactive Streamlit dashboard only

```bash
python main.py --dashboard
```

---

## CLI Arguments Reference

| Argument | Type | Default | Description |
|---|---|---|---|
| `--dashboard` | flag | off | Launch Streamlit dashboard and exit (skips pipeline) |
| `--noise` | `0` or `1` | `1` | Enable (1) or disable (0) Gaussian observation noise |
| `--sigma-r` | float | `50.0` | Position observation noise standard deviation (metres) |
| `--sigma-v` | float | `0.05` | Velocity observation noise standard deviation (m/s) |
| `--state PX PY PZ VX VY VZ` | 6 floats | ISS orbit | Initial orbital state vector in ECI frame (metres, m/s) |
| `--filter` | `ekf` or `ukf` | `ekf` | Kalman filter type for state estimation |
| `--maneuver-time` | float | `0.0` | Time since epoch (seconds) to apply impulsive dV |
| `--maneuver-dv DVR DVT DVN` | 3 floats | `0 0 0` | dV in RTN coordinates (Radial, Transverse, Normal) in m/s |

---

## Module Reference

### Physics Engine (Rust) — `src/physics/`

The core of the system. Compiled to a standalone binary (`physics_core` / `physics_core.exe`) and invoked as a subprocess by the Python orchestrator.

#### `constants.rs`
Defines all physical constants used across the engine:
- `MU_EARTH = 3.986004418e14 m^3/s^2` — Earth gravitational parameter
- `R_EARTH = 6378137.0 m` — WGS-84 equatorial radius
- `J2 = 1.08262668e-3`, `J3`, `J4` — Zonal harmonic coefficients
- `OMEGA_EARTH = 7.2921151467e-5 rad/s` — Earth rotation rate
- Drag: `Cd = 2.2`, `A/m = 0.01 m^2/kg`, exponential density model at 400 km
- SRP: `P_SRP = 4.56e-6 N/m^2`, `Cr = 1.2`
- Third-body: `MU_SUN`, `MU_MOON`

#### `dynamics.rs`
Aggregates all accelerations into the state derivative used by the integrator:
```
x_ddot = a_gravity + a_J2 + a_J3 + a_J4 + a_drag + a_srp + a_sun + a_moon
```

#### `j2.rs`
Implements J2, J3, and J4 zonal harmonic perturbations — the dominant non-spherical Earth gravity effects that cause orbital precession.

#### `drag.rs`
Exponential atmospheric density model. Accounts for Earth's atmospheric co-rotation when computing the relative velocity of the satellite through the atmosphere.

#### `srp.rs`
Solar Radiation Pressure with a cylindrical Earth shadow model. The satellite is considered in full eclipse when the perpendicular distance from the Earth-Sun axis falls within Earth's radius.

#### `third_body.rs`
Analytical Sun and Moon position models. Computes the gravitational acceleration from each body using the standard two-body point-mass formula.

#### `rk4.rs`
Fixed-step 4th-order Runge-Kutta integrator. Takes a state derivative function and advances `(r, v)` by one time step `dt`.

#### `propagator.rs`
Multi-step trajectory propagator. Wraps `rk4_step` to produce a full trajectory. Also provides a covariance-propagation variant used to evolve the initial estimation covariance.

#### `noise.rs`
Injects independent Gaussian noise into position (sigma_r) and velocity (sigma_v) components of an OrbitalState, simulating realistic sensor measurement errors.

#### `estimation.rs`
Implements two orbit-determination algorithms:

- **Batch Least Squares (`fit_orbit`)**: Iteratively solves the normal equations `(H^T H) dx = H^T b` using LU decomposition. The Jacobian `H` is computed numerically via finite differences over the full trajectory.
- **Extended Kalman Filter (`run_ekf`)**: Sequential filter with a numerical State Transition Matrix (STM) for the predict step and a position-only measurement update. Process noise Q and measurement noise R are diagonal.

#### `ukf.rs`
**Unscented Kalman Filter** — a derivative-free alternative to the EKF. Generates 13 sigma points (2N+1 for N=6) around the current state, propagates each through the nonlinear dynamics, and recombines with weighted means and covariances. More robust than EKF for highly nonlinear regimes.

#### `conjunction.rs`
Parallelised conjunction screening using **Rayon**:
1. Parses the full CelesTrak TLE catalog.
2. For each satellite, propagates with SGP4 over the full time window.
3. Finds the Time of Closest Approach (TCA) and minimum miss distance.
4. If within the 200 km warning threshold, computes **Foster's 2D Probability of Collision (Pc)** by:
   - Combining target and debris position covariances.
   - Projecting onto the B-plane (encounter plane) perpendicular to relative velocity.
   - Evaluating the 2D Gaussian integral over the combined hard-body radius (20 m).
5. Returns results sorted by collision probability (highest first).

---

### Catalog & TLE Fetcher (Python) — `src/catalog/`

#### `celestrak.py`
Downloads the **CelesTrak active satellite TLE catalog** (`GP_GROUP=active`). Caches the file at `data/cache/active.tle` to avoid redundant fetches. If the network request fails, automatically generates **500 synthetic LEO debris objects** with randomised orbital elements (seeded for reproducibility).

#### `run_celestrak_reference.py`
Generates a **SGP4 reference trajectory** for the ISS using a hardcoded TLE. Reads the time window from `time_reference.json` and writes `data/generated/reference_sgp4.csv`. This provides an independent, real-world trajectory for comparison against the physics engine output.

---

### Coordinate Conversion (Python) — `src/coords/`

Converts all ECI (Earth-Centred Inertial) trajectories to Earth-fixed geodetic coordinates.

#### `time.py`
Computes **Greenwich Mean Sidereal Time (GMST)** from UTC, which defines the rotation angle between ECI and ECEF frames.

#### `eci_to_ecef.py`
Applies the GMST rotation matrix `R_z(-theta_GMST)` to convert ECI position vectors to the Earth-Centred Earth-Fixed (ECEF) frame.

#### `ecef_to_lla.py`
Converts ECEF Cartesian coordinates to geodetic **Latitude / Longitude / Altitude** using the iterative Bowring method on the WGS-84 ellipsoid.

#### `run_coordinate_pipeline.py`
Batch-processes all generated ECI CSV files (`truth.csv`, `observed.csv`, `estimated.csv`, `reference_sgp4.csv`) and writes corresponding `*_lla.csv` files. The dashboard uses these for ground-track mapping.

---

### Statistical Analysis (R) — `src/analysis/`

Optional stage. Skipped automatically if `Rscript` is not on `PATH`.

#### `main.R`
Orchestrates the full statistical workflow:
1. Loads truth, observed, and estimated trajectories from `data/generated/`.
2. Computes **position and velocity residuals** (observed - truth, estimated - truth).
3. Calculates: **RMSE**, **mean error**, **max error**, **standard deviation**.
4. Writes a structured JSON report to `data/generated/statistics.json`.

---

### Visualization (Python) — `src/viz/`

#### `main.py`
Generates three static matplotlib figures saved to `data/generated/`:

| Output File | Content |
|---|---|
| `orbit_comparison_2d.png` | 2D XY-plane plot: truth (green), observed noise (red scatter), estimated (cyan dashed) |
| `orbit_comparison_3d.png` | 3D ECI orbit with Earth sphere; truth vs estimated |
| `conjunction_map_3d.png` | 3D orbit with threat satellite positions highlighted at TCA |

#### `dashboard.py`
A full **Streamlit web application** with a dark space-themed UI. Features include:
- Live pipeline execution controls (run, configure noise/filter/maneuver from the sidebar)
- **3D interactive globe** (Plotly) showing ground tracks for all trajectories
- Estimation error metric cards (position RMSE, velocity RMSE, Kalman filter errors)
- Conjunction warning table with probability of collision and TCA timestamps
- Tabbed layout for orbit comparison, conjunction analysis, covariance evolution, and statistics

---

## Generated Outputs

All files are written to `data/generated/`:

| File | Producer | Content |
|---|---|---|
| `truth.csv` | Rust engine | Ground-truth ECI trajectory (t, x, y, z, vx, vy, vz) |
| `observed.csv` | Rust engine | Noisy observation trajectory |
| `estimated.csv` | Rust engine | Batch Least Squares estimated trajectory |
| `ekf.csv` | Rust engine | Kalman Filter (EKF or UKF) estimated trajectory |
| `estimated_covariance.csv` | Rust engine | Filter covariance diagonal at each step (p_xx ... p_zz) |
| `estimation_metrics.json` | Rust engine | Initial & RMSE position/velocity errors |
| `conjunctions.json` | Rust engine | Close-approach records sorted by Pc |
| `reference_sgp4.csv` | Python catalog | ISS SGP4 reference trajectory |
| `truth_lla.csv` | Python coords | Ground-truth geodetic coordinates |
| `observed_lla.csv` | Python coords | Observed geodetic coordinates |
| `estimated_lla.csv` | Python coords | Estimated geodetic coordinates |
| `reference_sgp4_lla.csv` | Python coords | SGP4 reference geodetic coordinates |
| `statistics.json` | R analysis | RMSE, mean, max, SD for observation and tracking errors |
| `orbit_comparison_2d.png` | Python viz | 2D orbit comparison plot |
| `orbit_comparison_3d.png` | Python viz | 3D orbit comparison plot |
| `conjunction_map_3d.png` | Python viz | 3D conjunction proximity map |

---

## Interactive Dashboard

```bash
# Option 1: via the main pipeline CLI
python main.py --dashboard

# Option 2: directly with Streamlit
python -m streamlit run src/viz/dashboard.py
```

The dashboard opens at `http://localhost:8501` with:
- **Sidebar controls** — configure and re-run the full pipeline without leaving the browser.
- **Globe view** — interactive 3D Plotly globe showing all trajectory ground tracks.
- **Metrics panel** — live estimation accuracy cards.
- **Conjunction table** — sortable table of all detected close approaches with Pc values.
- **Covariance plots** — position uncertainty (1-sigma) evolution over time.

---

## Testing

Tests are located in `tests/` and use **pytest**.

```bash
# Run all tests
pytest tests/ -v

# Run individual test files
pytest tests/test_orbit_determination.py -v
pytest tests/test_conjunctions.py -v
pytest tests/test_coordinate_transforms.py -v
```

| Test | What it verifies |
|---|---|
| `test_orbit_determination.py` | Runs the Rust binary with low noise; asserts position error < 5 m and velocity error < 0.01 m/s after convergence |
| `test_conjunctions.py` | Validates that `conjunctions.json` is generated, non-empty, and contains all required fields |
| `test_coordinate_transforms.py` | Validates the ECI -> LLA coordinate conversion pipeline |

> **Note**: Tests automatically build the Rust binary if it has not been compiled yet.

---

## Offline Mode

If the CelesTrak server is unreachable (no internet, firewall, or rate limit), the system falls back automatically:

1. `celestrak.py` catches the network exception.
2. **500 synthetic LEO debris objects** are generated with randomised inclinations, RAANs, eccentricities, argument of perigees, mean anomalies, and mean motions.
3. The synthetic catalog is written to `data/cache/active.tle` and used for conjunction screening exactly as if it were a real catalog.

Synthetic objects use a fixed random seed (`np.random.seed(42)`) for full reproducibility.

---

*Built with Rust + Python + R*
