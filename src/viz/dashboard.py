import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone
from sgp4.api import Satrec, jday

# ============================================================
# Resolve Paths
# ============================================================
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
GENERATED_DIR = DATA_DIR / "generated"
CACHE_DIR = DATA_DIR / "cache"
TIME_REF_PATH = ROOT / "time_reference.json"

# ============================================================
# Page Configuration & Aesthetics
# ============================================================
st.set_page_config(
    page_title="Astrodynamics Tracker & Conjunction Warning Center",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium CSS
st.markdown("""
<style>
    /* Dark mode background overrides */
    .stApp {
        background-color: #030712;
        color: #f3f4f6;
        font-family: 'Outfit', 'Inter', -apple-system, sans-serif;
    }
    
    /* Title and headers */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700;
        letter-spacing: -0.025em;
    }
    
    /* Metric Cards */
    .metric-card {
        background-color: #0b1128;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -4px rgba(0, 0, 0, 0.3);
        border: 1px solid #1e293b;
        text-align: center;
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        border-color: #00f0ff;
        box-shadow: 0 10px 20px -3px rgba(0, 240, 255, 0.15);
        transform: translateY(-2px);
    }
    .metric-label {
        font-size: 13px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 800;
        color: #00f0ff;
    }
    .metric-subvalue {
        font-size: 12px;
        color: #64748b;
        margin-top: 4px;
    }
    
    /* Conjunction Risk badges */
    .badge-high {
        background-color: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        padding: 4px 8px;
        border-radius: 6px;
        border: 1px solid #ef4444;
        font-weight: bold;
        font-size: 11px;
    }
    .badge-warn {
        background-color: rgba(245, 158, 11, 0.2);
        color: #f59e0b;
        padding: 4px 8px;
        border-radius: 6px;
        border: 1px solid #f59e0b;
        font-weight: bold;
        font-size: 11px;
    }
    .badge-low {
        background-color: rgba(16, 185, 129, 0.2);
        color: #10b981;
        padding: 4px 8px;
        border-radius: 6px;
        border: 1px solid #10b981;
        font-weight: bold;
        font-size: 11px;
    }
    
    /* Log console styling */
    .log-console {
        background-color: #010409;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 15px;
        font-family: 'Courier New', Courier, monospace;
        color: #8b949e;
        max-height: 250px;
        overflow-y: auto;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Helper Functions
# ============================================================
@st.cache_data
def load_tles_from_db():
    from src.catalog.celestrak import fetch_active_tles
    from src.catalog.catalog_reader import read_tles
    try:
        tle_path = fetch_active_tles(CACHE_DIR)
        tles = read_tles(tle_path)
        return tles, None
    except Exception as e:
        return [], str(e)


def get_tle_initial_state(l1, l2, epoch_utc):
    try:
        sat = Satrec.twoline2rv(l1, l2)
        jd, fr = jday(
            epoch_utc.year,
            epoch_utc.month,
            epoch_utc.day,
            epoch_utc.hour,
            epoch_utc.minute,
            epoch_utc.second + epoch_utc.microsecond * 1e-6,
        )
        error, r, v = sat.sgp4(jd, fr)
        if error != 0:
            return None, f"SGP4 propagation error code: {error}"
        pos = [coord * 1000.0 for coord in r]
        vel = [coord * 1000.0 for coord in v]
        return (pos, vel), None
    except Exception as e:
        return None, str(e)

def write_time_reference(epoch_str, dt, steps):
    TIME_REF_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TIME_REF_PATH.open("w") as f:
        json.dump({
            "epoch_utc": epoch_str,
            "dt_seconds": dt,
            "steps": steps
        }, f, indent=2)

def run_tracking_pipeline(enable_noise, sigma_r, sigma_v, state_vector, filter_choice, man_time, man_dv):
    cmd = [
        sys.executable,
        str(ROOT / "main.py"),
        "--noise", "1" if enable_noise else "0",
        "--sigma-r", str(sigma_r),
        "--sigma-v", str(sigma_v),
        "--filter", filter_choice,
        "--maneuver-time", str(man_time),
        "--maneuver-dv", str(man_dv[0]), str(man_dv[1]), str(man_dv[2])
    ]
    if state_vector:
        cmd.extend(["--state"] + [str(x) for x in state_vector])
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT)
    return result.returncode, result.stdout

def is_land(lat, lon):
    """
    Programmatic low-resolution continent bounding box lookup.
    Used to texture the Earth sphere.
    """
    if lat < -60: # Antarctica
        return True
    if 15 <= lat <= 80 and -168 <= lon <= -50: # North America
        return True
    if -56 <= lat <= 15 and -82 <= lon <= -34: # South America
        return True
    if -35 <= lat <= 38 and -20 <= lon <= 51: # Africa
        return True
    if 10 <= lat <= 80 and -10 <= lon <= 170: # Eurasia
        return True
    if -45 <= lat <= -10 and 113 <= lon <= 153: # Australia
        return True
    return False

@st.cache_data
def get_earth_texture_colors(n):
    """
    Tries to load or download an Earth texture image to map to the 3D sphere.
    Falls back to analytical is_land if offline or failed.
    """
    u_vals = np.linspace(0, 2 * np.pi, n)
    v_vals = np.linspace(0, np.pi, n)
    cache_file = CACHE_DIR / "earth_lowres.jpg"
    url = "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Earthmap1000x500compac.jpg/640px-Earthmap1000x500compac.jpg"
    
    img_loaded = False
    if not cache_file.exists():
        try:
            import requests
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cache_file.write_bytes(response.content)
                img_loaded = True
        except Exception:
            pass
    else:
        img_loaded = True
        
    if img_loaded:
        try:
            import matplotlib.image as mpimg
            img = mpimg.imread(str(cache_file))
            H, W = img.shape[0], img.shape[1]
            surface_colors = np.zeros((n, n))
            
            for i in range(n):
                for j in range(n):
                    # Map latitude and longitude grids to pixel rows/cols
                    row = int(v_vals[j] / np.pi * (H - 1))
                    col = int(((u_vals[i] / (2 * np.pi) + 0.5) % 1.0) * (W - 1))
                    
                    pixel = img[row, col]
                    if len(pixel.shape) == 0:
                        val = float(pixel)
                    else:
                        r, g, b = float(pixel[0]), float(pixel[1]), float(pixel[2])
                        val = 0.2989 * r + 0.5870 * g + 0.1140 * b
                    surface_colors[i, j] = val
                    
            # Normalize surface_colors
            cmin, cmax = surface_colors.min(), surface_colors.max()
            if cmax > cmin:
                surface_colors = (surface_colors - cmin) / (cmax - cmin)
            return surface_colors, True
        except Exception:
            pass
            
    # Fallback to programmatic continents
    surface_colors = np.zeros((n, n))
    for i, u in enumerate(u_vals):
        for j, v in enumerate(v_vals):
            lat_deg = 90.0 - np.degrees(v)
            lon_deg = np.degrees(u) - 180.0
            if is_land(lat_deg, lon_deg):
                surface_colors[i, j] = 1.0
            else:
                surface_colors[i, j] = 0.0
    return surface_colors, False



def lla_to_ecef(lat, lon, alt):
    rad_lat = np.radians(lat)
    rad_lon = np.radians(lon)
    a = 6378137.0
    f = 1.0 / 298.257223563
    e2 = 2 * f - f * f
    N = a / np.sqrt(1.0 - e2 * np.sin(rad_lat) * np.sin(rad_lat))
    x = (N + alt) * np.cos(rad_lat) * np.cos(rad_lon)
    y = (N + alt) * np.cos(rad_lat) * np.sin(rad_lon)
    z = (N * (1.0 - e2) + alt) * np.sin(rad_lat)
    return np.array([x, y, z])

def calculate_elevation(sat_lat, sat_lon, sat_alt, gs_lat, gs_lon, gs_alt):
    sat_ecef = lla_to_ecef(sat_lat, sat_lon, sat_alt)
    gs_ecef = lla_to_ecef(gs_lat, gs_lon, gs_alt)
    
    r_vec = sat_ecef - gs_ecef
    range_m = np.linalg.norm(r_vec)
    if range_m == 0:
        return 0.0, 0.0, 0.0
        
    rad_lat = np.radians(gs_lat)
    rad_lon = np.radians(gs_lon)
    
    # Zenith vector
    zx = np.cos(rad_lat) * np.cos(rad_lon)
    zy = np.cos(rad_lat) * np.sin(rad_lon)
    zz = np.sin(rad_lat)
    u_z = np.array([zx, zy, zz])
    
    elevation = np.degrees(np.arcsin(np.dot(r_vec, u_z) / range_m))
    
    # North vector
    nx = -np.sin(rad_lat) * np.cos(rad_lon)
    ny = -np.sin(rad_lat) * np.sin(rad_lon)
    nz = np.cos(rad_lat)
    u_n = np.array([nx, ny, nz])
    
    # East vector
    ex = -np.sin(rad_lon)
    ey = np.cos(rad_lon)
    ez = 0.0
    u_e = np.array([ex, ey, ez])
    
    s = np.dot(r_vec, u_n)
    e = np.dot(r_vec, u_e)
    azimuth = np.degrees(np.arctan2(e, s)) % 360.0
    
    return elevation, azimuth, range_m

def project_covariance_to_bplane(cov3d_row, r_target, v_rel, r_rel):
    v_rel_mag = np.linalg.norm(v_rel)
    if v_rel_mag == 0:
        return None
    h_hat = v_rel / v_rel_mag
    
    tx = h_hat[1]*r_target[2] - h_hat[2]*r_target[1]
    ty = h_hat[2]*r_target[0] - h_hat[0]*r_target[2]
    tz = h_hat[0]*r_target[1] - h_hat[1]*r_target[0]
    t_mag = np.linalg.norm([tx, ty, tz])
    if t_mag == 0:
        return None
    t_hat = np.array([tx, ty, tz]) / t_mag
    
    n_hat = np.cross(h_hat, t_hat)
    
    x_b = np.dot(r_rel, t_hat)
    y_b = np.dot(r_rel, n_hat)
    
    P_3D = np.array([
        [cov3d_row['p_xx'], cov3d_row['p_xy'], cov3d_row['p_xz']],
        [cov3d_row['p_xy'], cov3d_row['p_yy'], cov3d_row['p_yz']],
        [cov3d_row['p_xz'], cov3d_row['p_yz'], cov3d_row['p_zz']]
    ])
    
    M_proj = np.vstack([t_hat, n_hat])
    P_2D = M_proj @ P_3D @ M_proj.T
    
    return x_b, y_b, P_2D[0, 0], P_2D[1, 1], P_2D[0, 1]

# ============================================================
# UI Structure & Sidebar
# ============================================================
st.title("🌌 Astrodynamics Tracker & Conjunction Warning Center")
st.markdown("Real-time auto-running space tracking system showing high-fidelity physical propagation and EKF/UKF metrics.")

# 1. Load active TLE database
tles, load_err = load_tles_from_db()
if load_err:
    st.error(f"Failed to load satellite catalog: {load_err}")
    st.stop()

st.sidebar.header("🕹️ Controls & Config")

# Satellite selector
tle_names = [t[0] for t in tles]
default_idx = 0
for idx, name in enumerate(tle_names):
    if "ISS (ZARYA)" in name:
        default_idx = idx
        break

selected_sat_name = st.sidebar.selectbox(
    "Select Target Satellite/Debris",
    options=tle_names,
    index=default_idx,
    help="Search and select a satellite from the active NORAD database."
)

# Extract selected TLE lines
selected_tle = next(t for t in tles if t[0] == selected_sat_name)
tle_name, tle_l1, tle_l2 = selected_tle

st.sidebar.markdown("---")
st.sidebar.markdown("**Selected TLE Data:**")
st.sidebar.code(f"{tle_l1}\n{tle_l2}", language="text")

st.sidebar.markdown("---")
st.sidebar.markdown("**Simulation Parameters:**")
steps = st.sidebar.slider("Trajectory Steps", min_value=100, max_value=1000, value=540, step=10)
dt = st.sidebar.slider("Step Size (dt, seconds)", min_value=1, max_value=60, value=10, step=1)

st.sidebar.markdown("---")
filter_choice = st.sidebar.selectbox("Estimation Filter", ["EKF", "UKF"], index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("**Tracking Noise Parameters:**")
enable_noise = st.sidebar.checkbox("Add Observation Noise", value=True)
sigma_r = st.sidebar.slider("Position Noise (σ_r, meters)", min_value=1.0, max_value=200.0, value=50.0, step=1.0)
sigma_v = st.sidebar.slider("Velocity Noise (σ_v, m/s)", min_value=0.01, max_value=1.00, value=0.05, step=0.01)

st.sidebar.markdown("---")
warning_threshold_km = st.sidebar.slider("Conjunction Warning Limit (km)", min_value=50, max_value=500, value=200, step=10)

# Maneuver Planner
st.sidebar.markdown("---")
st.sidebar.markdown("**🔥 Maneuver Planner**")
man_time = st.sidebar.number_input("Burn Time (s since epoch)", min_value=0.0, value=0.0, step=10.0)
man_dvr = st.sidebar.number_input("ΔV Radial (m/s)", value=0.0, step=0.1)
st_dvt = st.sidebar.number_input("ΔV In-Track (m/s)", value=0.0, step=0.1)
st_dvn = st.sidebar.number_input("ΔV Cross-Track (m/s)", value=0.0, step=0.1)
man_dv = [man_dvr, st_dvt, st_dvn]

# Ground Station Planner
st.sidebar.markdown("---")
st.sidebar.markdown("**📡 Ground Station**")
gs_lat = st.sidebar.number_input("Latitude (deg)", value=13.0827, step=0.01)
gs_lon = st.sidebar.number_input("Longitude (deg)", value=80.2707, step=0.01)
gs_alt = st.sidebar.number_input("Altitude (m)", value=10.0, step=1.0)

# Define file paths
truth_path = GENERATED_DIR / "truth.csv"
observed_path = GENERATED_DIR / "observed.csv"
estimated_path = GENERATED_DIR / "estimated.csv"
ekf_path = GENERATED_DIR / "ekf.csv"
truth_lla_path = GENERATED_DIR / "truth_lla.csv"
estimated_lla_path = GENERATED_DIR / "estimated_lla.csv"
conjunctions_path = GENERATED_DIR / "conjunctions.json"
metrics_path = GENERATED_DIR / "estimation_metrics.json"
stats_path = GENERATED_DIR / "statistics.json"
covariance_path = GENERATED_DIR / "estimated_covariance.csv"

# ============================================================
# Real-Time Auto-Run Execution
# ============================================================
epoch_utc = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

# Run simulation automatically whenever script triggers a rerun
write_time_reference(epoch_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), dt, steps)
state_info, sgp4_err = get_tle_initial_state(tle_l1, tle_l2, epoch_utc)

if sgp4_err:
    st.sidebar.error(f"SGP4 error: {sgp4_err}")
    state_vector = None
else:
    pos, vel = state_info
    state_vector = pos + vel

# Execute tracking pipeline silently (spinner feedback only)
with st.spinner("Re-propagating orbit and screening debris field..."):
    ret_code, stdout = run_tracking_pipeline(
        enable_noise, sigma_r, sigma_v, state_vector, filter_choice.lower(), man_time, man_dv
    )

if ret_code != 0:
    st.sidebar.error("Simulation failed! Check pipeline logs.")

with st.sidebar.expander("🛠️ Mission Execution Logs", expanded=False):
    st.markdown(f'<div class="log-console"><pre>{stdout}</pre></div>', unsafe_allow_html=True)

# Load Output Data
try:
    with open(conjunctions_path, "r") as f:
        conjunctions = json.load(f)
except:
    conjunctions = []

try:
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
except:
    metrics = {}

try:
    with open(stats_path, "r") as f:
        stats = json.load(f)
except:
    stats = {}

# ============================================================
# KPI Metrics Board
# ============================================================
st.markdown("### 📊 Astrodynamics Performance Metrics")
cols = st.columns(5)

with cols[0]:
    val = f"{metrics.get('initial_position_error_m', 0.0):.2f} m"
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">OD Init Pos Error</div><div class="metric-value">{val}</div><div class="metric-subvalue">Least Squares Fit vs Truth</div></div>', 
        unsafe_allow_html=True
    )
with cols[1]:
    val = f"{stats.get('tracking_error', {}).get('rmse_pos_m', 0.0):.2f} m"
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">Trajectory Pos RMSE</div><div class="metric-value">{val}</div><div class="metric-subvalue">Batch Orbit vs Truth</div></div>', 
        unsafe_allow_html=True
    )
with cols[2]:
    val = f"{metrics.get('ekf_final_position_error_m', 0.0):.2f} m"
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">Filter Final Error</div><div class="metric-value">{val}</div><div class="metric-subvalue">Sequential Tracking at End</div></div>', 
        unsafe_allow_html=True
    )
with cols[3]:
    val = f"{stats.get('observation_error', {}).get('rmse_pos_m', 0.0):.2f} m"
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">Sensor Noise RMSE</div><div class="metric-value">{val}</div><div class="metric-subvalue">Noisy Observations vs Truth</div></div>', 
        unsafe_allow_html=True
    )
with cols[4]:
    closest_dist = "N/A"
    if conjunctions:
        closest_dist = f"{conjunctions[0]['min_distance_m'] / 1000.0:.2f} km"
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">Closest approach</div><div class="metric-value">{closest_dist}</div><div class="metric-subvalue">Minimum Miss Distance</div></div>', 
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# Main Dashboard Tabs
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌐 3D Space Visualization", 
    "🗺️ Ground Tracks Map", 
    "📈 Error & Residuals", 
    "🎯 B-Plane Risk",
    "📡 Pass Planner",
    "⚠️ Conjunction Warnings"
])

# ------------------------------------------------------------
# Tab 1: 3D Orbit Map with realistic Earth globe
# ------------------------------------------------------------
with tab1:
    st.markdown("### 🌐 Interactive 3D Orbit Viewer")
    st.markdown("Visualize orbits in Earth-Centered Inertial (ECI) coordinate frame over a programmatically textured Earth globe.")
    
    fig_3d = go.Figure()
    
    # 1. Add Textured Earth Sphere
    R_EARTH_KM = 6378.137
    n = 72
    u_vals = np.linspace(0, 2 * np.pi, n)
    v_vals = np.linspace(0, np.pi, n)
    
    # Coordinates of sphere
    x_e = R_EARTH_KM * np.outer(np.cos(u_vals), np.sin(v_vals))
    y_e = R_EARTH_KM * np.outer(np.sin(u_vals), np.sin(v_vals))
    z_e = R_EARTH_KM * np.outer(np.ones_like(u_vals), np.cos(v_vals))
    
    # Generate Earth colors from texture or fallback
    surface_colors, is_textured = get_earth_texture_colors(n)

                
    # High-fidelity Earth colorscale mapping grayscale values
    if is_textured:
        earth_colorscale = [
            [0.0, '#050b14'],   # Space/very deep ocean
            [0.15, '#081726'],  # Deep ocean
            [0.4, '#0f2b48'],   # Medium ocean
            [0.48, '#1d4872'],  # Coastal water
            [0.51, '#7bb8d8'],  # Shallow/reef
            [0.53, '#d5c396'],  # Beach/sand
            [0.57, '#5d8a66'],  # Grass/vegetation
            [0.68, '#3c6e47'],  # Forest green
            [0.78, '#2e5138'],  # Dense forest
            [0.85, '#5c4e3c'],  # Hills/dry land
            [0.93, '#423528'],  # Mountains
            [1.0, '#ffffff']    # Snow/clouds
        ]
    else:
        # Fallback simplified green/blue colorscale
        earth_colorscale = [
            [0.0, '#0a1128'],  # Deep ocean
            [0.49, '#1c2d5a'], # Shallow water
            [0.5, '#2d5a27'],  # Coast/land green
            [1.0, '#193b16']   # Forest green
        ]

    
    fig_3d.add_trace(go.Surface(
        x=x_e, y=y_e, z=z_e,
        surfacecolor=surface_colors,
        colorscale=earth_colorscale,
        showscale=False,
        opacity=0.9,
        name="Earth",
        hoverinfo="skip"
    ))
    
    # Add Gridlines
    for lat in np.linspace(-np.pi/2, np.pi/2, 9):
        theta = np.linspace(0, 2*np.pi, 72)
        gl_x = R_EARTH_KM * np.cos(lat) * np.cos(theta)
        gl_y = R_EARTH_KM * np.cos(lat) * np.sin(theta)
        gl_z = R_EARTH_KM * np.sin(lat) * np.ones_like(theta)
        fig_3d.add_trace(go.Scatter3d(x=gl_x, y=gl_y, z=gl_z, mode='lines', line=dict(color='rgba(255,255,255,0.08)', width=1), showlegend=False, hoverinfo='skip'))
        
    for lon in np.linspace(0, 2*np.pi, 12):
        phi = np.linspace(-np.pi/2, np.pi/2, 72)
        gl_x = R_EARTH_KM * np.cos(phi) * np.cos(lon)
        gl_y = R_EARTH_KM * np.cos(phi) * np.sin(lon)
        gl_z = R_EARTH_KM * np.sin(phi)
        fig_3d.add_trace(go.Scatter3d(x=gl_x, y=gl_y, z=gl_z, mode='lines', line=dict(color='rgba(255,255,255,0.08)', width=1), showlegend=False, hoverinfo='skip'))
        
    # 2. Plot Trajectories
    if truth_path.exists():
        df_truth = pd.read_csv(truth_path)
        fig_3d.add_trace(go.Scatter3d(
            x=df_truth['x'] / 1000.0,
            y=df_truth['y'] / 1000.0,
            z=df_truth['z'] / 1000.0,
            mode='lines',
            line=dict(color='#10b981', width=3.5),
            name="Ground Truth"
        ))
        
    if estimated_path.exists():
        df_est = pd.read_csv(estimated_path)
        fig_3d.add_trace(go.Scatter3d(
            x=df_est['x'] / 1000.0,
            y=df_est['y'] / 1000.0,
            z=df_est['z'] / 1000.0,
            mode='lines',
            line=dict(color='#06b6d4', width=2.5, dash='dash'),
            name="Estimated (Batch)"
        ))
        
    if ekf_path.exists():
        df_ekf = pd.read_csv(ekf_path)
        fig_3d.add_trace(go.Scatter3d(
            x=df_ekf['x'] / 1000.0,
            y=df_ekf['y'] / 1000.0,
            z=df_ekf['z'] / 1000.0,
            mode='lines',
            line=dict(color='#d946ef', width=2.5, dash='dot'),
            name=f"Sequential ({filter_choice})"
        ))
        
    if observed_path.exists() and enable_noise:
        df_obs = pd.read_csv(observed_path)
        step_sample = max(1, len(df_obs) // 60)
        df_obs_sampled = df_obs.iloc[::step_sample]
        fig_3d.add_trace(go.Scatter3d(
            x=df_obs_sampled['x'] / 1000.0,
            y=df_obs_sampled['y'] / 1000.0,
            z=df_obs_sampled['z'] / 1000.0,
            mode='markers',
            marker=dict(color='#ef4444', size=3, opacity=0.8),
            name="Noisy Observations"
        ))
        
    # 3. Add Close Approaches
    threshold_m = warning_threshold_km * 1000.0
    valid_conjs = [c for c in conjunctions if c['min_distance_m'] <= threshold_m]
    
    for c in valid_conjs[:5]:
        sat_pos = np.array(c['sat_position_m'])
        rel_pos = np.array(c['relative_position_m'])
        target_pos = sat_pos - rel_pos
        
        t_pos_km = target_pos / 1000.0
        s_pos_km = sat_pos / 1000.0
        
        fig_3d.add_trace(go.Scatter3d(
            x=[t_pos_km[0], s_pos_km[0]],
            y=[t_pos_km[1], s_pos_km[1]],
            z=[t_pos_km[2], s_pos_km[2]],
            mode='lines+markers',
            line=dict(color='#f59e0b', width=3, dash='longdash'),
            marker=dict(size=4, color=['#06b6d4', '#ef4444']),
            name=f"Approach: {c['sat_name']} ({c['min_distance_m']/1000.0:.2f} km)"
        ))

    # Layout styling
    fig_3d.update_layout(
        scene=dict(
            xaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="#1e293b", showbackground=False, title="X (km)", color="#94a3b8"),
            yaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="#1e293b", showbackground=False, title="Y (km)", color="#94a3b8"),
            zaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="#1e293b", showbackground=False, title="Z (km)", color="#94a3b8"),
            aspectmode='data'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, b=0, t=0),
        legend=dict(
            yanchor="top",
            y=0.95,
            xanchor="left",
            x=0.02,
            font=dict(color="#f3f4f6"),
            bgcolor="rgba(3,7,18,0.75)"
        ),
        height=750
    )
    
    st.plotly_chart(fig_3d, use_container_width=True)

# ------------------------------------------------------------
# Tab 2: Ground Tracks
# ------------------------------------------------------------
with tab2:
    st.markdown("### 🗺️ Ground Tracks (WGS84 LLA Coordinates)")
    
    if truth_lla_path.exists():
        df_truth_lla = pd.read_csv(truth_lla_path)
        times_list = df_truth_lla['time'].tolist()
        
        step_idx = st.slider("Time timeline scrub", min_value=0, max_value=len(times_list)-1, value=0)
        curr_time = times_list[step_idx]
        curr_pt = df_truth_lla.iloc[step_idx]
        
        st.markdown(f"**Current position at T+{curr_time:.1f} s:** Lat = `{curr_pt['lat']:.4f}°`, Lon = `{curr_pt['lon']:.4f}°`")
        
        fig_gt = go.Figure()
        
        fig_gt.add_trace(go.Scattergeo(
            lon=df_truth_lla['lon'],
            lat=df_truth_lla['lat'],
            mode='lines',
            line=dict(color='#10b981', width=2),
            name="Ground Truth"
        ))
        
        if estimated_lla_path.exists():
            df_est_lla = pd.read_csv(estimated_lla_path)
            fig_gt.add_trace(go.Scattergeo(
                lon=df_est_lla['lon'],
                lat=df_est_lla['lat'],
                mode='lines',
                line=dict(color='#06b6d4', width=2, dash='dash'),
                name="Estimated (Batch)"
            ))
            
        fig_gt.add_trace(go.Scattergeo(
            lon=[curr_pt['lon']],
            lat=[curr_pt['lat']],
            mode='markers',
            marker=dict(color='#d946ef', size=10, symbol='circle'),
            name="Current Position"
        ))
        
        fig_gt.update_geos(
            showcoastlines=True, coastlinecolor="#1e3a8a",
            showland=True, landcolor="#0f172a",
            showocean=True, oceancolor="#020617",
            showlakes=True, lakecolor="#020617",
            showcountries=True, countrycolor="#334155",
            projection_type="equirectangular",
            bgcolor="rgba(0,0,0,0)"
        )
        
        fig_gt.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="#f3f4f6"),
            margin=dict(l=0, r=0, b=0, t=30),
            legend=dict(
                yanchor="top",
                y=0.95,
                xanchor="left",
                x=0.02,
                bgcolor="rgba(3,7,18,0.75)"
            ),
            height=600
        )
        
        st.plotly_chart(fig_gt, use_container_width=True)

# ------------------------------------------------------------
# Tab 3: Error & Residuals
# ------------------------------------------------------------
with tab3:
    st.markdown("### 📈 Orbit Determination & Filtering Residuals")
    
    col_err1, col_err2 = st.columns(2)
    
    if truth_path.exists() and estimated_path.exists():
        df_t = pd.read_csv(truth_path)
        df_e = pd.read_csv(estimated_path)
        df_ek = pd.read_csv(ekf_path) if ekf_path.exists() else None
        
        # Position Errors
        pos_err_batch = np.sqrt((df_e['x'] - df_t['x'])**2 + (df_e['y'] - df_t['y'])**2 + (df_e['z'] - df_t['z'])**2)
        
        fig_pos = go.Figure()
        fig_pos.add_trace(go.Scatter(
            x=df_t['time'], y=pos_err_batch,
            mode='lines',
            line=dict(color='#06b6d4', width=2),
            name="Batch Least Squares"
        ))
        
        if df_ek is not None:
            pos_err_ekf = np.sqrt((df_ek['x'] - df_t['x'])**2 + (df_ek['y'] - df_t['y'])**2 + (df_ek['z'] - df_t['z'])**2)
            fig_pos.add_trace(go.Scatter(
                x=df_t['time'], y=pos_err_ekf,
                mode='lines',
                line=dict(color='#d946ef', width=2),
                name=f"Filter ({filter_choice})"
            ))
            
        fig_pos.update_layout(
            title="3D Position Error Residuals",
            xaxis=dict(title="Time since epoch (seconds)", gridcolor="#1e293b"),
            yaxis=dict(title="Error (meters)", gridcolor="#1e293b"),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="#f3f4f6"),
            legend=dict(bgcolor="rgba(3,7,18,0.75)")
        )
        
        with col_err1:
            st.plotly_chart(fig_pos, use_container_width=True)
            
        # Velocity Errors
        vel_err_batch = np.sqrt((df_e['vx'] - df_t['vx'])**2 + (df_e['vy'] - df_t['vy'])**2 + (df_e['vz'] - df_t['vz'])**2)
        
        fig_vel = go.Figure()
        fig_vel.add_trace(go.Scatter(
            x=df_t['time'], y=vel_err_batch,
            mode='lines',
            line=dict(color='#06b6d4', width=2),
            name="Batch Least Squares"
        ))
        
        if df_ek is not None:
            vel_err_ekf = np.sqrt((df_ek['vx'] - df_t['vx'])**2 + (df_ek['vy'] - df_t['vy'])**2 + (df_ek['vz'] - df_t['vz'])**2)
            fig_vel.add_trace(go.Scatter(
                x=df_t['time'], y=vel_err_ekf,
                mode='lines',
                line=dict(color='#d946ef', width=2),
                name=f"Filter ({filter_choice})"
            ))
            
        fig_vel.update_layout(
            title="3D Velocity Error Residuals",
            xaxis=dict(title="Time since epoch (seconds)", gridcolor="#1e293b"),
            yaxis=dict(title="Error (m/s)", gridcolor="#1e293b"),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="#f3f4f6"),
            legend=dict(bgcolor="rgba(3,7,18,0.75)")
        )
        
        with col_err2:
            st.plotly_chart(fig_vel, use_container_width=True)

# ------------------------------------------------------------
# Tab 4: B-Plane Risk Analysis
# ------------------------------------------------------------
with tab4:
    st.markdown("### 🎯 Conjunction B-Plane Projection & Ellipse Analysis")
    
    if len(conjunctions) == 0:
        st.info("No screened approaches available.")
    else:
        col_bp1, col_bp2 = st.columns([2, 1])
        
        with col_bp2:
            st.markdown("**Select Conjunction Event:**")
            bp_names = [f"{c['sat_name']} (Miss: {c['min_distance_m']/1000.0:.2f} km)" for c in conjunctions]
            selected_conj_idx = st.selectbox("Event", range(len(bp_names)), format_func=lambda i: bp_names[i])
            
            c = conjunctions[selected_conj_idx]
            
            # Load Covariance at TCA step
            r_sat = np.array(c['sat_position_m'])
            r_rel = np.array(c['relative_position_m'])
            v_rel = np.array(c['relative_velocity_m_s'])
            r_target = r_sat - r_rel
            
            if covariance_path.exists():
                df_cov = pd.read_csv(covariance_path)
                tca_step = max(0, min(len(df_cov)-1, int(round(c['tca_seconds'] / dt)) - 1))
                cov_row = df_cov.iloc[tca_step]
                
                # Project
                proj = project_covariance_to_bplane(cov_row, r_target, v_rel, r_rel)
                
                if proj is not None:
                    x_b, y_b, pxx, pyy, pxy = proj
                    
                    # Eigenvalues
                    tr = pxx + pyy
                    det_cov = pxx * pyy - pxy * pxy
                    diff = np.sqrt(max(0.0, (tr/2)**2 - det_cov))
                    l1 = tr/2 + diff
                    l2 = tr/2 - diff
                    
                    a = np.sqrt(max(0.0, l1))
                    b = np.sqrt(max(0.0, l2))
                    theta = 0.5 * np.arctan2(2 * pxy, pxx - pyy)
                    
                    # 3-Sigma Ellipse
                    angles = np.linspace(0, 2*np.pi, 100)
                    ex = 3.0 * a * np.cos(angles)
                    ey = 3.0 * b * np.sin(angles)
                    ellipse_x = ex * np.cos(theta) - ey * np.sin(theta)
                    ellipse_y = ex * np.sin(theta) + ey * np.cos(theta)
                    
                    # 20m Collision Circle
                    r_coll = 20.0
                    circle_x = x_b + r_coll * np.cos(angles)
                    circle_y = y_b + r_coll * np.sin(angles)
                    
                    # Alfano Pc
                    det_val = max(1e-12, pxx * pyy - pxy * pxy)
                    alfano_pc = (r_coll * r_coll) / (2.0 * np.e * np.sqrt(det_val))
                    
                    st.markdown("---")
                    st.markdown(f"**Debris Target:** `{c['sat_name']}`")
                    st.markdown(f"**Catalog ID:** `{c['sat_id']}`")
                    st.markdown(f"**Miss Distance:** `{c['min_distance_m']/1000.0:.3f} km`")
                    st.markdown(f"**TCA:** `{c['tca_seconds']:.1f} s`")
                    st.markdown(f"**Pc (Foster):** `{c['probability_of_collision']:.4e}`")
                    st.markdown(f"**Alfano Max Pc:** `{alfano_pc:.4e}`")
            else:
                st.warning("Covariance output data missing.")
                proj = None
                
        with col_bp1:
            if proj is not None:
                fig_bp = go.Figure()
                
                # Covariance Ellipse
                fig_bp.add_trace(go.Scatter(
                    x=ellipse_x, y=ellipse_y,
                    mode='lines',
                    line=dict(color='#00f0ff', width=2),
                    fill='toself',
                    fillcolor='rgba(0, 240, 255, 0.05)',
                    name='3-Sigma Covariance'
                ))
                
                # Collision bound
                fig_bp.add_trace(go.Scatter(
                    x=circle_x, y=circle_y,
                    mode='lines',
                    line=dict(color='#ef4444', width=2),
                    fill='toself',
                    fillcolor='rgba(239, 68, 68, 0.1)',
                    name='Collision circle (R_coll = 20m)'
                ))
                
                # Debris Point
                fig_bp.add_trace(go.Scatter(
                    x=[x_b], y=[y_b],
                    mode='markers+text',
                    marker=dict(color='#f59e0b', size=10, symbol='x'),
                    text=['Debris TCA'],
                    textposition='top center',
                    name='Debris relative pos'
                ))
                
                # Target Center
                fig_bp.add_trace(go.Scatter(
                    x=[0], y=[0],
                    mode='markers',
                    marker=dict(color='#10b981', size=8),
                    name='Tracked Satellite'
                ))
                
                fig_bp.update_layout(
                    title=f"B-Plane Projection: {c['sat_name']}",
                    xaxis=dict(title="T axis (meters)", gridcolor="#1e293b", scaleanchor='y', scaleratio=1),
                    yaxis=dict(title="N axis (meters)", gridcolor="#1e293b"),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color="#f3f4f6"),
                    legend=dict(bgcolor="rgba(3,7,18,0.75)", x=0.02, y=0.95),
                    height=550
                )
                
                st.plotly_chart(fig_bp, use_container_width=True)

# ------------------------------------------------------------
# Tab 5: Pass Planner
# ------------------------------------------------------------
with tab5:
    st.markdown("### 📡 Ground Station Visibility Pass Predictions")
    
    if estimated_lla_path.exists():
        df_est_lla = pd.read_csv(estimated_lla_path)
        
        el_mask = 10.0
        passes = []
        
        for idx, row in df_est_lla.iterrows():
            el, az, rng = calculate_elevation(row['lat'], row['lon'], row['alt'], gs_lat, gs_lon, gs_alt)
            if el >= el_mask:
                passes.append({
                    "Time (s)": row['time'],
                    "Elevation (deg)": f"{el:.1f}°",
                    "Azimuth (deg)": f"{az:.1f}°",
                    "Range (km)": f"{rng/1000.0:.2f} km"
                })
                
        col_pass1, col_pass2 = st.columns([2, 1])
        
        with col_pass2:
            st.markdown(f"**Visibility Windows (above {el_mask}° mask):**")
            if passes:
                st.dataframe(pd.DataFrame(passes), height=350)
            else:
                st.info("No passes detected above 10° horizon mask.")
                
        with col_pass1:
            elevations = []
            times = df_est_lla['time'].tolist()
            for idx, row in df_est_lla.iterrows():
                el, _, _ = calculate_elevation(row['lat'], row['lon'], row['alt'], gs_lat, gs_lon, gs_alt)
                elevations.append(max(0, el))
                
            fig_pass = go.Figure()
            fig_pass.add_trace(go.Scatter(
                x=times, y=elevations,
                mode='lines',
                line=dict(color='#10b981', width=3),
                fill='tozeroy',
                fillcolor='rgba(16, 185, 129, 0.1)',
                name="Pass Profile"
            ))
            fig_pass.add_trace(go.Scatter(
                x=[times[0], times[-1]], y=[el_mask, el_mask],
                mode='lines',
                line=dict(color='#ef4444', dash='dash', width=1.5),
                name=" Horizon Mask"
            ))
            
            fig_pass.update_layout(
                title="Ground Station Elevation Profile",
                xaxis=dict(title="Time (s)", gridcolor="#1e293b"),
                yaxis=dict(title="Elevation Angle (deg)", gridcolor="#1e293b", range=[0, 90]),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#f3f4f6"),
                legend=dict(bgcolor="rgba(3,7,18,0.75)")
            )
            st.plotly_chart(fig_pass, use_container_width=True)

# ------------------------------------------------------------
# Tab 6: Conjunction warnings
# ------------------------------------------------------------
with tab6:
    st.markdown("### ⚠️ Screened Debris Conjunction Warnings")
    
    if len(conjunctions) == 0:
        st.info(f"No objects detected within the {warning_threshold_km} km screening threshold.")
    else:
        rows = []
        for idx, c in enumerate(conjunctions):
            dist_km = c['min_distance_m'] / 1000.0
            pc = c['probability_of_collision']
            
            if pc > 1e-4 or dist_km < 10.0:
                badge_class = "badge-high"
                risk_level = "CRITICAL"
            elif pc > 1e-6 or dist_km < 100.0:
                badge_class = "badge-warn"
                risk_level = "WARNING"
            else:
                badge_class = "badge-low"
                risk_level = "INFO"
                
            pc_str = f"{pc:.4e}" if pc > 0 else "0.0"
            
            rows.append({
                "Rank": idx + 1,
                "Debris Name": c['sat_name'],
                "Catalog #": c['sat_id'],
                "Miss Distance (km)": f"{dist_km:.3f}",
                "TCA (seconds)": f"{c['tca_seconds']:.1f}",
                "Risk Level": f'<span class="{badge_class}">{risk_level}</span>',
                "P_c (Foster)": pc_str
            })
            
        df_table = pd.DataFrame(rows)
        st.write(df_table.to_html(escape=False, index=False), unsafe_allow_html=True)
