import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
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
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap" rel="stylesheet">
<style>
    .stApp {
        background: radial-gradient(ellipse at 60% 0%, #0a1628 0%, #030712 60%);
        color: #f3f4f6;
        font-family: 'Outfit', 'Inter', -apple-system, sans-serif;
    }
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700;
        letter-spacing: -0.025em;
    }
    .metric-card {
        background: linear-gradient(135deg, #0b1128 0%, #0f1a35 100%);
        border-radius: 14px;
        padding: 18px 22px;
        box-shadow: 0 10px 25px -5px rgba(0,0,0,0.4);
        border: 1px solid #1e2d4a;
        text-align: center;
        transition: all 0.25s ease;
    }
    .metric-card:hover {
        border-color: #00f0ff;
        box-shadow: 0 0 20px rgba(0,240,255,0.18), 0 10px 25px -5px rgba(0,0,0,0.5);
        transform: translateY(-3px);
    }
    .metric-label {
        font-size: 11px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 800;
        background: linear-gradient(90deg, #00f0ff, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .metric-subvalue {
        font-size: 11px;
        color: #475569;
        margin-top: 4px;
    }
    .badge-high {
        background-color: rgba(239,68,68,0.15);
        color: #ef4444;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid #ef4444;
        font-weight: 700;
        font-size: 10px;
        letter-spacing: 0.05em;
    }
    .badge-warn {
        background-color: rgba(245,158,11,0.15);
        color: #f59e0b;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid #f59e0b;
        font-weight: 700;
        font-size: 10px;
        letter-spacing: 0.05em;
    }
    .badge-low {
        background-color: rgba(16,185,129,0.15);
        color: #10b981;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid #10b981;
        font-weight: 700;
        font-size: 10px;
        letter-spacing: 0.05em;
    }
    .log-console {
        background-color: #010409;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 12px;
        font-family: 'Courier New', Courier, monospace;
        color: #64748b;
        max-height: 220px;
        overflow-y: auto;
        font-size: 11px;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #060d1a 0%, #030712 100%);
        border-right: 1px solid #1e293b;
    }
</style>
""", unsafe_allow_html=True)

ST_CARD_STYLE = """
<style>
.orbit-kpi-row { display: flex; gap: 12px; flex-wrap: wrap; margin: 12px 0; }
.orbit-kpi { background: linear-gradient(135deg,#0b1128,#0f1a35); border-radius:12px; padding:14px 18px;
             border:1px solid #1e2d4a; flex:1; min-width:130px; text-align:center; }
.orbit-kpi .lbl { font-size:10px; color:#64748b; text-transform:uppercase; letter-spacing:.08em; }
.orbit-kpi .val { font-size:18px; font-weight:800; color:#00f0ff; }
.orbit-kpi .unit { font-size:10px; color:#475569; margin-top:2px; }
.timeline-jump-row { display:flex; gap:8px; margin:10px 0; flex-wrap:wrap; }
.avoidance-card { background:linear-gradient(135deg,#1a0520,#1f0530); border:1px solid #7c3aed;
                  border-radius:14px; padding:18px 22px; margin:12px 0; }
.avoidance-card h4 { color:#d946ef; margin:0 0 8px 0; font-size:14px; }
.avoidance-rec { font-size:22px; font-weight:800; color:#a855f7; margin:6px 0; }
.avoidance-detail { font-size:12px; color:#94a3b8; }
.tle-age-ok  { color:#10b981; font-size:11px; font-weight:600; }
.tle-age-warn{ color:#f59e0b; font-size:11px; font-weight:600; }
.tle-age-old { color:#ef4444; font-size:11px; font-weight:600; }
</style>
"""


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

@st.cache_resource
def get_satrec_objects():
    tles, err = load_tles_from_db()
    if err or not tles:
        return [], []
    sat_objects = []
    sat_names = []
    for name, l1, l2 in tles:
        try:
            sat = Satrec.twoline2rv(l1, l2)
            sat_objects.append(sat)
            sat_names.append(name)
        except Exception:
            pass
    return sat_objects, sat_names

def propagate_constellation(sat_objects, epoch_utc, curr_time):
    from datetime import timedelta
    target_dt = epoch_utc + timedelta(seconds=curr_time)
    jd, fr = jday(
        target_dt.year, target_dt.month, target_dt.day,
        target_dt.hour, target_dt.minute, target_dt.second + target_dt.microsecond * 1e-6
    )
    
    xs, ys, zs = [], [], []
    for sat in sat_objects:
        error, r, v = sat.sgp4(jd, fr)
        if error == 0:
            xs.append(r[0])  # SGP4 returns km
            ys.append(r[1])
            zs.append(r[2])
    return np.array(xs), np.array(ys), np.array(zs)


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


# ============================================================
# Advanced Analytics Helper Functions
# ============================================================

MU_EARTH_KM3 = 398600.4418  # km³/s²

def state_to_elements(r_km, v_km_s):
    """Convert ECI state to classical Keplerian orbital elements."""
    r = np.asarray(r_km, dtype=float)
    v = np.asarray(v_km_s, dtype=float)
    r_norm = np.linalg.norm(r)
    v_norm = np.linalg.norm(v)
    eps = 0.5 * v_norm**2 - MU_EARTH_KM3 / r_norm
    if abs(eps) < 1e-12:
        return None
    a = -MU_EARTH_KM3 / (2.0 * eps)
    h_vec = np.cross(r, v)
    h_norm = np.linalg.norm(h_vec)
    e_vec = np.cross(v, h_vec) / MU_EARTH_KM3 - r / r_norm
    e = np.linalg.norm(e_vec)
    i = np.degrees(np.arccos(np.clip(h_vec[2] / h_norm, -1.0, 1.0)))
    T_min = 2.0 * np.pi * np.sqrt(max(a, 1.0)**3 / MU_EARTH_KM3) / 60.0
    return {"a_km": a, "e": e, "i_deg": i, "T_min": T_min}


def compute_eclipse_mask(df_truth_m, epoch_utc):
    """Return boolean array True = in Earth shadow using sun ephemeris."""
    R_E = 6378.137  # km
    AU = 1.495978707e8  # km
    mask = []
    for _, row in df_truth_m.iterrows():
        t_sec = float(row['time'])
        days = 8765.5 + t_sec / 86400.0
        g = np.radians((357.528 + 0.9856003 * days) % 360.0)
        l = np.radians((280.460 + 0.9856474 * days) % 360.0)
        lam = l + np.radians(1.915 * np.sin(g) + 0.020 * np.sin(2 * g))
        obliq = np.radians(23.439)
        r_sun = np.array([AU * np.cos(lam),
                           AU * np.sin(lam) * np.cos(obliq),
                           AU * np.sin(lam) * np.sin(obliq)])
        r_sat = np.array([row['x'] / 1000.0, row['y'] / 1000.0, row['z'] / 1000.0])
        u_sun = r_sun / np.linalg.norm(r_sun)
        d_along = np.dot(r_sat, u_sun)
        in_shadow = False
        if d_along < 0.0:
            r_sq = np.dot(r_sat, r_sat)
            d_perp = np.sqrt(max(0.0, r_sq - d_along * d_along))
            in_shadow = d_perp < R_E
        mask.append(in_shadow)
    return np.array(mask)


def get_covariance_ellipsoid_mesh(pos_km, cov_row, scale_factor=500.0, sigma=3.0):
    """Eigen-decompose 3x3 position covariance and return ellipsoid surface mesh in ECI km."""
    P3 = np.array([
        [cov_row['p_xx'], cov_row['p_xy'], cov_row['p_xz']],
        [cov_row['p_xy'], cov_row['p_yy'], cov_row['p_yz']],
        [cov_row['p_xz'], cov_row['p_yz'], cov_row['p_zz']]
    ], dtype=float)
    try:
        eigenvalues, eigenvectors = np.linalg.eigh(P3)
    except Exception:
        return None
    eigenvalues = np.maximum(eigenvalues, 1e-12)
    semi_axes = sigma * np.sqrt(eigenvalues) * scale_factor / 1000.0  # m -> km scaled
    n_u, n_v = 32, 18
    u_p = np.linspace(0, 2 * np.pi, n_u)
    v_p = np.linspace(0, np.pi, n_v)
    xs = semi_axes[0] * np.outer(np.cos(u_p), np.sin(v_p))
    ys = semi_axes[1] * np.outer(np.sin(u_p), np.sin(v_p))
    zs = semi_axes[2] * np.outer(np.ones(n_u), np.cos(v_p))
    pts = np.stack([xs.ravel(), ys.ravel(), zs.ravel()])
    rot = eigenvectors @ pts
    return (rot[0].reshape(n_u, n_v) + pos_km[0],
            rot[1].reshape(n_u, n_v) + pos_km[1],
            rot[2].reshape(n_u, n_v) + pos_km[2])


def detect_gs_passes(df_lla, gs_lat, gs_lon, gs_alt_m, el_mask_deg=10.0):
    """Detect visibility pass windows. Returns list of {aos_time, los_time, max_el}."""
    passes = []
    in_pass = False
    aos_t = 0.0
    max_el = 0.0
    for _, row in df_lla.iterrows():
        try:
            el, _, _ = calculate_elevation(row['lat'], row['lon'], row['alt'], gs_lat, gs_lon, gs_alt_m)
        except Exception:
            continue
        if el >= el_mask_deg:
            if not in_pass:
                in_pass = True
                aos_t = float(row['time'])
                max_el = el
            else:
                max_el = max(max_el, el)
        else:
            if in_pass:
                in_pass = False
                passes.append({"aos_time": aos_t, "los_time": float(row['time']), "max_el": max_el})
    if in_pass:
        passes.append({"aos_time": aos_t, "los_time": float(df_lla['time'].iloc[-1]), "max_el": max_el})
    return passes


def build_event_timeline_chart(df_truth_m, df_ekf, conjunctions_list, man_time_s, passes, eclipse_mask):
    """Annotated orbit profile timeline: altitude, speed, filter error with event markers."""
    R_E = 6378.137
    times = df_truth_m['time'].values
    r = np.sqrt(df_truth_m['x']**2 + df_truth_m['y']**2 + df_truth_m['z']**2) / 1000.0
    alt_km = r - R_E
    speed = np.sqrt(df_truth_m['vx']**2 + df_truth_m['vy']**2 + df_truth_m['vz']**2) / 1000.0

    filter_err = None
    if df_ekf is not None and len(df_ekf) == len(df_truth_m):
        filter_err = np.sqrt(
            (df_ekf['x'].values - df_truth_m['x'].values)**2 +
            (df_ekf['y'].values - df_truth_m['y'].values)**2 +
            (df_ekf['z'].values - df_truth_m['z'].values)**2
        )

    fig = go.Figure()

    # Eclipse shading bands
    if eclipse_mask is not None and len(eclipse_mask) == len(times):
        in_ecl = False
        ecl_start = None
        for t, ecl in zip(times, eclipse_mask):
            if ecl and not in_ecl:
                in_ecl = True
                ecl_start = float(t)
            elif not ecl and in_ecl:
                in_ecl = False
                fig.add_vrect(x0=ecl_start, x1=float(t),
                              fillcolor='rgba(20,20,50,0.55)', layer='below', line_width=0)
        if in_ecl:
            fig.add_vrect(x0=ecl_start, x1=float(times[-1]),
                          fillcolor='rgba(20,20,50,0.55)', layer='below', line_width=0)

    # GS pass windows
    for p in passes[:5]:
        fig.add_vrect(x0=p['aos_time'], x1=p['los_time'],
                      fillcolor='rgba(16,185,129,0.10)', layer='below', line_width=0)

    # Altitude trace
    fig.add_trace(go.Scatter(
        x=times, y=alt_km, name='Altitude (km)',
        mode='lines', line=dict(color='#06b6d4', width=2),
        fill='tozeroy', fillcolor='rgba(6,182,212,0.07)', yaxis='y'
    ))
    # Speed trace
    fig.add_trace(go.Scatter(
        x=times, y=speed, name='Speed (km/s)',
        mode='lines', line=dict(color='#a855f7', width=1.5, dash='dot'),
        yaxis='y2', opacity=0.8
    ))
    # Filter error
    if filter_err is not None:
        fig.add_trace(go.Scatter(
            x=times, y=filter_err, name='Filter Error (m)',
            mode='lines', line=dict(color='#f43f5e', width=1.5),
            yaxis='y', opacity=0.85
        ))

    # Event vertical lines
    if man_time_s > 0:
        fig.add_vline(x=man_time_s, line_dash='dash', line_color='#d946ef', line_width=2,
                      annotation_text='🚀 Burn', annotation_position='top right',
                      annotation_font_color='#d946ef', annotation_font_size=11)
    if conjunctions_list:
        tca = conjunctions_list[0].get('tca_seconds', 0)
        fig.add_vline(x=tca, line_dash='dash', line_color='#f59e0b', line_width=2,
                      annotation_text='⚠️ TCA', annotation_position='top left',
                      annotation_font_color='#f59e0b', annotation_font_size=11)
    for p in passes[:2]:
        fig.add_vline(x=p['aos_time'], line_dash='longdash', line_color='#10b981', line_width=1,
                      annotation_text='📡 AOS', annotation_position='top right',
                      annotation_font_color='#10b981', annotation_font_size=9)
        fig.add_vline(x=p['los_time'], line_dash='longdash', line_color='#ef4444', line_width=1,
                      annotation_text='LOS', annotation_position='top left',
                      annotation_font_color='#ef4444', annotation_font_size=9)

    fig.update_layout(
        height=240,
        margin=dict(l=0, r=50, b=0, t=28),
        paper_bgcolor='rgba(2,5,15,1)',
        plot_bgcolor='rgba(5,10,25,0.8)',
        title=dict(text='🛸 Mission Orbit Profile & Event Timeline',
                   font=dict(color='#cbd5e1', size=13)),
        xaxis=dict(title='Mission Time (s)', color='#64748b', gridcolor='#1e293b',
                   tickfont=dict(size=10)),
        yaxis=dict(title='Altitude (km) / Error (m)', color='#64748b',
                   gridcolor='#1e293b', side='left'),
        yaxis2=dict(title='Speed (km/s)', color='#a855f7', overlaying='y', side='right',
                    showgrid=False, tickfont=dict(color='#a855f7', size=10)),
        legend=dict(bgcolor='rgba(3,7,18,0.75)', font=dict(color='#cbd5e1', size=10),
                    orientation='h', y=-0.28, x=0),
        font=dict(color='#f3f4f6'),
    )
    return fig


def compute_avoidance_burn_recommendation(target_pos_m, target_vel_m, tca_seconds, dt_s):
    """
    Search over candidate RIC burns [-2, +2] m/s to maximize miss distance at TCA.
    Returns {dv_mag, component, projected_miss_km}.
    Uses fast Euler integration as a proxy (called once per critical conjunction).
    """
    r_km = np.array(target_pos_m) / 1000.0
    v_km_s = np.array(target_vel_m) / 1000.0
    tca_steps = max(1, int(round(tca_seconds / dt_s)))

    r_hat = r_km / np.linalg.norm(r_km)
    h_vec = np.cross(r_km, v_km_s)
    h_norm = np.linalg.norm(h_vec)
    if h_norm < 1e-9:
        return None
    h_hat = h_vec / h_norm
    t_hat = np.cross(h_hat, r_hat)
    ric_axes = {"radial": r_hat, "in-track": t_hat, "cross-track": h_hat}

    best = {"dv_mag": 0.0, "component": "in-track", "projected_miss_km": 0.0, "delta_miss_km": 0.0}

    def propagate_fast(r0, v0, n_steps):
        """Fast Euler propagation of Keplerian orbit."""
        rr, vv = r0.copy(), v0.copy()
        for _ in range(n_steps):
            r_n = np.linalg.norm(rr)
            a = -MU_EARTH_KM3 / r_n**3 * rr
            vv = vv + a * dt_s
            rr = rr + vv * dt_s
        return rr

    # Baseline position at TCA (no burn)
    r_tca_base = propagate_fast(r_km, v_km_s, tca_steps)

    for comp, axis in ric_axes.items():
        for dv_m_s in np.arange(-2.0, 2.05, 0.25):
            if abs(dv_m_s) < 0.1:
                continue
            dv_km_s = axis * dv_m_s / 1000.0  # m/s -> km/s
            r_tca_new = propagate_fast(r_km, v_km_s + dv_km_s, tca_steps)
            # Displacement from baseline = proxy for miss improvement
            delta = np.linalg.norm(r_tca_new - r_tca_base)
            if delta > best["projected_miss_km"]:
                best = {
                    "dv_mag": dv_m_s,
                    "component": comp,
                    "projected_miss_km": delta,
                    "delta_miss_km": delta,
                }
    return best



def _is_land(lat, lon):
    """Coarse continent bounding boxes as fallback when no image available."""
    if lat < -60:                                          return True   # Antarctica
    if 15 <= lat <= 80 and -168 <= lon <= -50:             return True   # N America
    if -56 <= lat <= 15 and -82 <= lon <= -34:             return True   # S America

    if -35 <= lat <= 38 and -20 <= lon <= 51:              return True   # Africa
    if 10 <= lat <= 80 and -10 <= lon <= 170:              return True   # Eurasia
    if -45 <= lat <= -10 and 113 <= lon <= 153:            return True   # Australia
    return False


@st.cache_data(show_spinner=False)
def get_earth_texture_colors(n_lon: int, n_lat: int):
    """
    Downloads (once) a Blue Marble Earth map and returns a 2-D surfacecolor
    array shaped (n_lon, n_lat) aligned to Plotly Surface convention:

        x[i, j] = R * cos(u[i]) * sin(v[j])
        y[i, j] = R * sin(u[i]) * sin(v[j])
        z[i, j] = R * cos(v[j])

    where  u[i] = longitude  0 -> 2*pi  (left = 0 deg, right = 360 deg)
           v[j] = colatitude 0 -> pi    (top  = North Pole)

    surfacecolor[i, j]  maps to the point at (u[i], v[j]).
    Image convention: col 0 = left edge (0 deg E), row 0 = top (90 deg N)
    => after resize to (W=n_lon, H=n_lat):  gray[row, col] = gray[j, i]
    => surfacecolor[i, j] = gray[j, i]  i.e. surfacecolor = gray.T
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "earth_blue_marble.jpg"

    urls = [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Earthmap1000x500compac.jpg/1280px-Earthmap1000x500compac.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Earthmap1000x500compac.jpg/640px-Earthmap1000x500compac.jpg",
    ]

    if not cache_file.exists():
        try:
            import requests
            for url in urls:
                try:
                    resp = requests.get(url, timeout=10)
                    if resp.status_code == 200 and len(resp.content) > 20_000:
                        cache_file.write_bytes(resp.content)
                        break
                except Exception:
                    continue
        except ImportError:
            pass

    if cache_file.exists():
        try:
            from PIL import Image as _PILImg
            img = _PILImg.open(str(cache_file)).convert("RGB")
            # Resize so width = n_lon cols (longitude), height = n_lat rows (colatitude)
            img = img.resize((n_lon, n_lat), _PILImg.LANCZOS)
            arr = np.array(img, dtype=np.float32)           # shape (n_lat, n_lon, 3)
            # Luminance
            gray = 0.2989 * arr[:, :, 0] + 0.5870 * arr[:, :, 1] + 0.1140 * arr[:, :, 2]
            # Roll columns by n_lon // 2 to align 0 longitude with the center of the image
            gray = np.roll(gray, n_lon // 2, axis=1)
            # gray[row, col] = gray[j, i]  -> transpose to get [i, j]
            sc = gray.T.astype(np.float32)                   # shape (n_lon, n_lat)
            lo, hi = sc.min(), sc.max()
            if hi > lo:
                sc = (sc - lo) / (hi - lo)
            return sc, True
        except Exception:
            pass

    # Fallback: analytical continent bounding boxes
    u_v = np.linspace(0, 2 * np.pi, n_lon)
    v_v = np.linspace(0, np.pi, n_lat)
    sc = np.zeros((n_lon, n_lat), dtype=np.float32)
    for i, u in enumerate(u_v):
        lon_deg = np.degrees(u)
        if lon_deg > 180.0:
            lon_deg -= 360.0
        for j, v in enumerate(v_v):
            lat_deg = 90.0 - np.degrees(v)
            if _is_land(lat_deg, lon_deg):
                sc[i, j] = 1.0
    return sc, False


def get_visibility_cone_mesh(gs_lat, gs_lon, gs_alt, mask_deg=10.0, height_km=1500.0):
    gs_ecef = lla_to_ecef(gs_lat, gs_lon, gs_alt) / 1000.0 # convert to km
    
    rad_lat = np.radians(gs_lat)
    rad_lon = np.radians(gs_lon)
    
    # Zenith direction (normal to WGS84 ellipsoid at gs_lat, gs_lon)
    zenith = np.array([
        np.cos(rad_lat) * np.cos(rad_lon),
        np.cos(rad_lat) * np.sin(rad_lon),
        np.sin(rad_lat)
    ])
    
    # Create two orthogonal vectors in the tangent plane
    if abs(zenith[0]) < 0.9:
        ortho1 = np.cross(zenith, np.array([1.0, 0.0, 0.0]))
    else:
        ortho1 = np.cross(zenith, np.array([0.0, 1.0, 0.0]))
    ortho1 /= np.linalg.norm(ortho1)
    ortho2 = np.cross(zenith, ortho1)
    
    # Generate cone mesh grid  (vectorised)
    n_theta = 48
    n_h = 12
    theta_vals = np.linspace(0, 2 * np.pi, n_theta)
    h_vals = np.linspace(0, height_km, n_h)
    half_angle = np.radians(90.0 - mask_deg)

    # Shape: (n_h,)  and  (n_theta,) broadcast to (n_h, n_theta)
    r_vals = h_vals[:, None] * np.tan(half_angle)            # (n_h, 1)
    cos_th = np.cos(theta_vals)[None, :]                     # (1, n_theta)
    sin_th = np.sin(theta_vals)[None, :]                     # (1, n_theta)

    # gs_ecef + h*zenith + r*(cos*o1 + sin*o2)
    pts = (gs_ecef[:, None, None]                            # (3,1,1)
           + h_vals[None, :, None] * zenith[:, None, None]  # (3,n_h,1)
           + r_vals[None, :, :] * (cos_th * ortho1[:, None, None]
                                   + sin_th * ortho2[:, None, None]))  # (3,n_h,n_theta)

    x_c = pts[0]   # (n_h, n_theta)
    y_c = pts[1]
    z_c = pts[2]

    return x_c, y_c, z_c



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

# ── Catalog Intelligence ─────────────────────────────────
CONSTELLATIONS = {
    "All": lambda name: True,
    "Starlink": lambda name: "STARLINK" in name.upper(),
    "OneWeb": lambda name: "ONEWEB" in name.upper(),
    "GPS / NAVSTAR": lambda name: "GPS" in name.upper() or "NAVSTAR" in name.upper(),
    "Iridium": lambda name: "IRIDIUM" in name.upper(),
    "ISS / Tiangong": lambda name: "ISS" in name.upper() or "TIANHE" in name.upper() or "TIANGONG" in name.upper(),
    "Debris Only": lambda name: "DEB" in name.upper() or "R/B" in name.upper() or "DEBRIS" in name.upper(),
    "NOAA / GOES": lambda name: "NOAA" in name.upper() or "GOES" in name.upper(),
}

st.sidebar.markdown("**🛰️ Catalog Intelligence**")
col_cat1, col_cat2 = st.sidebar.columns([2, 1])
const_group = col_cat1.selectbox("Constellation", list(CONSTELLATIONS.keys()), index=0, label_visibility='collapsed')
if col_cat2.button("🔄 Refresh", help="Force re-download TLE catalog"):
    import shutil
    tle_cache = CACHE_DIR / "active.tle"
    if tle_cache.exists():
        tle_cache.unlink()
    st.cache_data.clear()
    st.rerun()

# TLE age badge
tle_cache_path = CACHE_DIR / "active.tle"
if tle_cache_path.exists():
    import os
    tle_age_days = (time.time() - os.path.getmtime(str(tle_cache_path))) / 86400.0
    age_cls = "tle-age-ok" if tle_age_days < 1 else ("tle-age-warn" if tle_age_days < 3 else "tle-age-old")
    age_icon = "✅" if tle_age_days < 1 else ("⚠️" if tle_age_days < 3 else "🔴")
    st.sidebar.markdown(f'<span class="{age_cls}">{age_icon} TLE age: {tle_age_days:.1f}d</span>', unsafe_allow_html=True)

sat_search = st.sidebar.text_input("🔍 Search Satellite", placeholder="e.g. ISS, Starlink-1234, 25544", label_visibility='visible')

# Filter TLEs by constellation group and search term
group_filter = CONSTELLATIONS[const_group]
filtered_tles = [t for t in tles if group_filter(t[0]) and (not sat_search or sat_search.lower() in t[0].lower() or sat_search in t[1])]
if not filtered_tles:
    filtered_tles = tles  # fallback to all if nothing matches

tle_names = [t[0] for t in filtered_tles]
default_idx = 0
for idx, name in enumerate(tle_names):
    if "ISS (ZARYA)" in name:
        default_idx = idx
        break

selected_sat_name = st.sidebar.selectbox(
    "Target Satellite",
    options=tle_names,
    index=min(default_idx, len(tle_names) - 1),
    help="Filtered from NORAD active catalog."
)
st.sidebar.caption(f"{len(filtered_tles):,} satellites shown")

# Extract selected TLE lines
selected_tle = next((t for t in filtered_tles if t[0] == selected_sat_name), filtered_tles[0])
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

# Visualization Controls
st.sidebar.markdown("---")
st.sidebar.markdown("**🔭 Visualization Settings**")
ellipsoid_scale = st.sidebar.selectbox(
    "3σ Uncertainty Ellipsoid",
    ["Disabled", "1× (physical)", "100×", "500×", "1,000×", "5,000×"],
    index=3,
    help="Scale factor for covariance ellipsoid visibility at Earth scale."
)
ellipsoid_scale_map = {
    "Disabled": 0,
    "1× (physical)": 1,
    "100×": 100,
    "500×": 500,
    "1,000×": 1000,
    "5,000×": 5000,
}
ellipsoid_scale_val = ellipsoid_scale_map[ellipsoid_scale]

st.sidebar.markdown("---")
st.sidebar.markdown("**📡 Ground Station**")
gs_lat = st.sidebar.number_input("Latitude (deg)", value=13.0827, step=0.01)
gs_lon = st.sidebar.number_input("Longitude (deg)", value=80.2707, step=0.01)
gs_alt = st.sidebar.number_input("Altitude (m)", value=10.0, step=1.0)

# Global Mission Clock & Animator
st.sidebar.markdown("---")
st.sidebar.markdown("**⏳ Global Mission Clock & Viewport**")
constellation_density = st.sidebar.selectbox(
    "Constellation Density",
    ["Disabled", "Low (500 sats)", "Medium (1,500 sats)", "High (5,000 sats)", "Full (15,000 sats)"],
    index=2
)
view_mode = st.sidebar.selectbox(
    "3D Camera Zoom Focus",
    ["Target Orbit (Auto)", "LEO Zoom (~8,500 km)", "MEO Zoom (~25,000 km)", "GEO Zoom (~45,000 km)"],
    index=0
)
play_mode = st.sidebar.checkbox("▶️ Auto-Play Animation", value=False)
anim_speed = st.sidebar.slider("Animation Speed (steps/frame)", 1, 20, 3, 1) if play_mode else 3

if "timeline_step" not in st.session_state:
    st.session_state.timeline_step = 0

if play_mode:
    st.session_state.timeline_step = (st.session_state.timeline_step + anim_speed) % steps

# Clamp in case steps slider changed
st.session_state.timeline_step = min(st.session_state.timeline_step, steps - 1)

step_idx = st.sidebar.slider(
    "Timeline Step Index",
    min_value=0, max_value=steps - 1,
    value=st.session_state.timeline_step,
    disabled=play_mode
)
if not play_mode:
    st.session_state.timeline_step = step_idx

curr_time = step_idx * dt


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

# ── Orbital Elements KPI Row 2 ────────────────────────────
st.markdown(ST_CARD_STYLE, unsafe_allow_html=True)
_kpi_els = None
try:
    if truth_path.exists():
        _df_kpi = pd.read_csv(truth_path)
        if len(_df_kpi) > 0:
            _row = _df_kpi.iloc[-1]
            _kpi_els = state_to_elements(
                [_row['x'] / 1000.0, _row['y'] / 1000.0, _row['z'] / 1000.0],
                [_row['vx'] / 1000.0, _row['vy'] / 1000.0, _row['vz'] / 1000.0]
            )
except Exception:
    pass

_pc_top = conjunctions[0]['probability_of_collision'] if conjunctions else 0.0
_eclipse_frac_str = "—"
try:
    if truth_path.exists():
        _df_ecl = pd.read_csv(truth_path)
        _ecl_mask = compute_eclipse_mask(_df_ecl, epoch_utc)
        _eclipse_frac_str = f"{100.0 * _ecl_mask.sum() / max(len(_ecl_mask), 1):.1f}%"
except Exception:
    pass

_el_a   = f"{_kpi_els['a_km']:.1f}" if _kpi_els else "—"
_el_e   = f"{_kpi_els['e']:.5f}" if _kpi_els else "—"
_el_i   = f"{_kpi_els['i_deg']:.2f}°" if _kpi_els else "—"
_el_T   = f"{_kpi_els['T_min']:.2f}" if _kpi_els else "—"
_pc_str = f"{_pc_top:.2e}" if _pc_top > 0 else "< 1e-12"

st.markdown(f"""
<div class="orbit-kpi-row">
  <div class="orbit-kpi"><div class="lbl">Semi-major Axis</div><div class="val">{_el_a}</div><div class="unit">km</div></div>
  <div class="orbit-kpi"><div class="lbl">Eccentricity</div><div class="val">{_el_e}</div><div class="unit">—</div></div>
  <div class="orbit-kpi"><div class="lbl">Inclination</div><div class="val">{_el_i}</div><div class="unit">degrees</div></div>
  <div class="orbit-kpi"><div class="lbl">Orbit Period</div><div class="val">{_el_T}</div><div class="unit">minutes</div></div>
  <div class="orbit-kpi"><div class="lbl">Eclipse Fraction</div><div class="val">{_eclipse_frac_str}</div><div class="unit">of arc</div></div>
  <div class="orbit-kpi"><div class="lbl">Top Pc (Foster)</div><div class="val">{_pc_str}</div><div class="unit">probability</div></div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# Main Dashboard Tabs
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🌐 3D Space Visualization", 
    "🗺️ Ground Tracks Map", 
    "📈 Error & Residuals", 
    "🎯 B-Plane Risk",
    "📡 Pass Planner",
    "⚠️ Conjunction Warnings",
    "📊 Orbital Analytics"
])


# ─────────────────────────────────────────────────────────────
# Tab 1: Live 3D Globe
# ─────────────────────────────────────────────────────────────
with tab1:
    st.markdown("### 🌐 Live 3D ECI Orbit Viewer")
    st.markdown(
        f"Epoch **{epoch_utc.strftime('%Y-%m-%d %H:%M UTC')}** · "
        f"T+**{curr_time:.0f} s** (step {step_idx}/{steps})"
    )

    fig_3d = go.Figure()

    # ── 1. Earth Globe ──────────────────────────────────────
    R_E = 6378.137  # km
    omega_e = 7.292115e-5  # rad/s
    theta_rotation = omega_e * curr_time

    # u = longitude  0…2π  (N_LON points) with dynamic rotation in ECI
    # v = colatitude 0…π   (N_LAT points)
    N_LON, N_LAT = 180, 90
    u = np.linspace(0, 2 * np.pi, N_LON) + theta_rotation
    v = np.linspace(0, np.pi,     N_LAT)

    # Sphere: x[i,j] corresponds to longitude u[i], colatitude v[j]
    x_e = R_E * np.outer(np.cos(u), np.sin(v))   # (N_LON, N_LAT)
    y_e = R_E * np.outer(np.sin(u), np.sin(v))   # (N_LON, N_LAT)
    z_e = R_E * np.outer(np.ones(N_LON), np.cos(v))  # (N_LON, N_LAT)

    # surfacecolor[i,j] → point (u[i], v[j])
    surface_colors, is_textured = get_earth_texture_colors(N_LON, N_LAT)

    if is_textured:
        earth_colorscale = [
            [0.00, '#03111f'],   # deep ocean
            [0.08, '#04213d'],
            [0.20, '#0c3b68'],   # mid-ocean
            [0.38, '#1a5a8a'],   # shallow
            [0.48, '#2e7aad'],
            [0.50, '#c8b98a'],   # coastline/sand
            [0.52, '#6b9c5e'],   # lowland green
            [0.62, '#4a7d43'],   # forest
            [0.72, '#3a6335'],
            [0.82, '#6b5e47'],   # highlands/rock
            [0.91, '#8a7a68'],   # mountains
            [1.00, '#e8e8e8'],   # snow/icecaps
        ]
    else:
        earth_colorscale = [
            [0.0, '#04213d'],
            [0.49, '#1a5a8a'],
            [0.50, '#3a6335'],
            [1.0,  '#4a7d43'],
        ]

    fig_3d.add_trace(go.Surface(
        x=x_e, y=y_e, z=z_e,
        surfacecolor=surface_colors,
        colorscale=earth_colorscale,
        showscale=False,
        opacity=1.0,
        name="Earth",
        hoverinfo="skip",
        lightposition=dict(x=2, y=1, z=1),
        lighting=dict(ambient=0.45, diffuse=0.7, specular=0.3, roughness=0.8)
    ))

    # ── 1a. Lat/Lon grid lines ───────────────────────────────
    for lat_deg in np.arange(-75, 91, 15):
        lat_r = np.radians(lat_deg)
        th = np.linspace(0, 2 * np.pi, 181)
        fig_3d.add_trace(go.Scatter3d(
            x=R_E * np.cos(lat_r) * np.cos(th),
            y=R_E * np.cos(lat_r) * np.sin(th),
            z=R_E * np.sin(lat_r) * np.ones_like(th),
            mode='lines', line=dict(color='rgba(255,255,255,0.07)', width=1),
            showlegend=False, hoverinfo='skip'
        ))

    for lon_deg in np.arange(0, 360, 30):
        lon_r = np.radians(lon_deg) + theta_rotation
        ph = np.linspace(-np.pi / 2, np.pi / 2, 91)
        fig_3d.add_trace(go.Scatter3d(
            x=R_E * np.cos(ph) * np.cos(lon_r),
            y=R_E * np.cos(ph) * np.sin(lon_r),
            z=R_E * np.sin(ph),
            mode='lines', line=dict(color='rgba(255,255,255,0.07)', width=1),
            showlegend=False, hoverinfo='skip'
        ))

    # Equator highlight
    th = np.linspace(0, 2 * np.pi, 361)
    fig_3d.add_trace(go.Scatter3d(
        x=R_E * np.cos(th), y=R_E * np.sin(th), z=np.zeros_like(th),
        mode='lines', line=dict(color='rgba(255,180,50,0.22)', width=1.5),
        showlegend=False, hoverinfo='skip'
    ))

    # ── 2. Ground Station (Earth-Rotating in ECI) ────────────
    rotated_lon = gs_lon + np.degrees(omega_e * curr_time)
    gs_pt = lla_to_ecef(gs_lat, rotated_lon, gs_alt) / 1000.0

    fig_3d.add_trace(go.Scatter3d(
        x=[gs_pt[0]], y=[gs_pt[1]], z=[gs_pt[2]],
        mode='markers+text',
        marker=dict(color='#10b981', size=7, symbol='diamond',
                    line=dict(color='#ffffff', width=1)),
        text=['GS'], textposition='top center',
        name='Ground Station'
    ))

    # Visibility cone
    cx, cy, cz = get_visibility_cone_mesh(gs_lat, rotated_lon, gs_alt, mask_deg=10.0, height_km=1500.0)
    fig_3d.add_trace(go.Surface(
        x=cx, y=cy, z=cz,
        colorscale=[[0, 'rgba(16,185,129,0.18)'], [1, 'rgba(16,185,129,0.01)']],
        showscale=False, name='Visibility Cone',
        hoverinfo='skip', opacity=0.7
    ))

    # ── 3. Satellite Constellation Point Cloud ───────────────
    if constellation_density != "Disabled":
        sat_objects, sat_names_list = get_satrec_objects()
        if sat_objects:
            total_sats = len(sat_objects)
            if constellation_density == "Low (500 sats)":
                step = max(1, total_sats // 500)
                sats_to_prop = sat_objects[::step]
            elif constellation_density == "Medium (1,500 sats)":
                step = max(1, total_sats // 1500)
                sats_to_prop = sat_objects[::step]
            elif constellation_density == "High (5,000 sats)":
                step = max(1, total_sats // 5000)
                sats_to_prop = sat_objects[::step]
            else:
                sats_to_prop = sat_objects

            s_xs, s_ys, s_zs = propagate_constellation(sats_to_prop, epoch_utc, curr_time)
            alts = np.sqrt(s_xs ** 2 + s_ys ** 2 + s_zs ** 2) - R_E
            fig_3d.add_trace(go.Scatter3d(
                x=s_xs, y=s_ys, z=s_zs,
                mode='markers',
                marker=dict(
                    size=1.2,
                    color=alts,
                    colorscale='Viridis',
                    cmin=200, cmax=36000,
                    opacity=0.5,
                    colorbar=dict(
                        title=dict(
                            text="Alt (km)",
                            font=dict(color="#94a3b8", size=10)
                        ),
                        thickness=8, len=0.4, y=0.18,
                        tickfont=dict(color="#94a3b8", size=10)
                    )
                ),
                name="Active Constellation",
                hoverinfo="skip"
            ))

    # ── 4. Target Satellite Trajectories ─────────────────────
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

        if len(df_truth) > step_idx:
            pt = df_truth.iloc[step_idx]
            fig_3d.add_trace(go.Scatter3d(
                x=[pt['x'] / 1000.0], y=[pt['y'] / 1000.0], z=[pt['z'] / 1000.0],
                mode='markers+text',
                marker=dict(color='#d946ef', size=9, symbol='circle',
                            line=dict(color='#ffffff', width=1.5)),
                text=[tle_name[:20]], textposition='top center',
                name='Target (Now)'
            ))

    if estimated_path.exists():
        df_est = pd.read_csv(estimated_path)
        fig_3d.add_trace(go.Scatter3d(
            x=df_est['x'] / 1000.0, y=df_est['y'] / 1000.0, z=df_est['z'] / 1000.0,
            mode='lines', line=dict(color='#06b6d4', width=2, dash='dash'),
            name="Estimated (Batch)"
        ))

    if ekf_path.exists():
        df_ekf = pd.read_csv(ekf_path)
        fig_3d.add_trace(go.Scatter3d(
            x=df_ekf['x'] / 1000.0, y=df_ekf['y'] / 1000.0, z=df_ekf['z'] / 1000.0,
            mode='lines', line=dict(color='#a855f7', width=2, dash='dot'),
            name=f"Sequential ({filter_choice})"
        ))

    if observed_path.exists() and enable_noise:
        df_obs = pd.read_csv(observed_path)
        samp = max(1, len(df_obs) // 80)
        df_s = df_obs.iloc[::samp]
        fig_3d.add_trace(go.Scatter3d(
            x=df_s['x'] / 1000.0, y=df_s['y'] / 1000.0, z=df_s['z'] / 1000.0,
            mode='markers',
            marker=dict(color='#ef4444', size=2.5, opacity=0.7),
            name="Noisy Observations"
        ))

    # ── 4b. Covariance Uncertainty Ellipsoid ─────────────────
    if ellipsoid_scale_val > 0 and covariance_path.exists() and ekf_path.exists():
        try:
            df_cov = pd.read_csv(covariance_path)
            df_ekf_ell = pd.read_csv(ekf_path)
            safe_cov_idx = min(step_idx, len(df_cov) - 1)
            safe_ekf_idx = min(step_idx, len(df_ekf_ell) - 1)
            cov_row = df_cov.iloc[safe_cov_idx]
            ekf_row = df_ekf_ell.iloc[safe_ekf_idx]
            pos_km = np.array([ekf_row['x'], ekf_row['y'], ekf_row['z']]) / 1000.0
            ell_mesh = get_covariance_ellipsoid_mesh(
                pos_km, cov_row, scale_factor=float(ellipsoid_scale_val)
            )
            if ell_mesh is not None:
                ex, ey, ez = ell_mesh
                fig_3d.add_trace(go.Surface(
                    x=ex, y=ey, z=ez,
                    colorscale=[[0, 'rgba(244,63,94,0.22)'], [1, 'rgba(244,63,94,0.28)']],
                    showscale=False,
                    opacity=0.30,
                    name=f"3σ Uncertainty ({ellipsoid_scale})",
                    hoverinfo='skip',
                    lighting=dict(ambient=0.9, diffuse=0.4, specular=0.1)
                ))
        except Exception:
            pass

    # ── 5. Close Approach Lines ──────────────────────────────
    threshold_m = warning_threshold_km * 1000.0
    for c in conjunctions[:5]:
        if c['min_distance_m'] > threshold_m:
            continue
        sat_pos = np.array(c['sat_position_m']) / 1000.0
        tgt_pos = (np.array(c['sat_position_m']) - np.array(c['relative_position_m'])) / 1000.0
        fig_3d.add_trace(go.Scatter3d(
            x=[tgt_pos[0], sat_pos[0]],
            y=[tgt_pos[1], sat_pos[1]],
            z=[tgt_pos[2], sat_pos[2]],
            mode='lines+markers',
            line=dict(color='#f59e0b', width=3, dash='longdash'),
            marker=dict(size=4, color=['#06b6d4', '#ef4444']),
            name=f"Approach: {c['sat_name'][:18]} ({c['min_distance_m']/1000.0:.1f} km)"
        ))

    # ── 5. Viewport Limit calculation ────────────────────────
    limit = 8500.0  # default for LEO
    if view_mode == "Target Orbit (Auto)":
        if truth_path.exists():
            try:
                df_truth = pd.read_csv(truth_path)
                max_r = np.sqrt(df_truth['x']**2 + df_truth['y']**2 + df_truth['z']**2).max() / 1000.0
                limit = max(8500.0, max_r * 1.15)
            except Exception:
                limit = 8500.0
    elif view_mode == "LEO Zoom (~8,500 km)":
        limit = 8500.0
    elif view_mode == "MEO Zoom (~25,000 km)":
        limit = 25000.0
    elif view_mode == "GEO Zoom (~45,000 km)":
        limit = 45000.0

    # ── Layout ───────────────────────────────────────────────
    fig_3d.update_layout(
        scene=dict(
            bgcolor='rgba(2,5,15,1)',
            xaxis=dict(showbackground=False, showgrid=False,
                       zeroline=False, showticklabels=False, title="", range=[-limit, limit]),
            yaxis=dict(showbackground=False, showgrid=False,
                       zeroline=False, showticklabels=False, title="", range=[-limit, limit]),
            zaxis=dict(showbackground=False, showgrid=False,
                       zeroline=False, showticklabels=False, title="", range=[-limit, limit]),
            aspectmode='manual',
            aspectratio=dict(x=1, y=1, z=1),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.0),
                up=dict(x=0, y=0, z=1),
                center=dict(x=0, y=0, z=0)
            )
        ),
        paper_bgcolor='rgba(2,5,15,1)',
        plot_bgcolor='rgba(2,5,15,1)',
        margin=dict(l=0, r=0, b=0, t=0),
        legend=dict(
            yanchor="top", y=0.97, xanchor="left", x=0.01,
            font=dict(color="#cbd5e1", size=11),
            bgcolor="rgba(3,7,18,0.82)",
            bordercolor="#1e293b", borderwidth=1
        ),
        height=780,
        uirevision="globe"  # Preserve camera across reruns
    )

    st.plotly_chart(fig_3d, width="stretch")

    # ── Jump Navigation Buttons ────────────────────────────
    _event_markers = [
        ("\u23ee\ufe0f Start", 0, "#475569"),
        ("\u2693 Maneuver", int(man_time / dt) if man_time > 0 else 0, "#d946ef"),
        ("\u26a0\ufe0f TCA", int(conjunctions[0]['tca_seconds'] / dt) if conjunctions else 0, "#f59e0b"),
        ("\u23ed\ufe0f End", steps - 1, "#06b6d4"),
    ]
    jb_cols = st.columns(len(_event_markers))
    for _col, (_label, _target_step, _color) in zip(jb_cols, _event_markers):
        if _col.button(_label, key=f"jump_{_label}"):
            st.session_state.timeline_step = max(0, min(_target_step, steps - 1))
            st.rerun()

    # ── Event Timeline Chart ──────────────────────────────
    try:
        _df_truth_tl = pd.read_csv(truth_path) if truth_path.exists() else None
        _df_ekf_tl = pd.read_csv(ekf_path) if ekf_path.exists() else None
        _ecl_mask_tl = None
        if _df_truth_tl is not None:
            _ecl_mask_tl = compute_eclipse_mask(_df_truth_tl, epoch_utc)
        _passes_tl = []
        if truth_lla_path.exists():
            _df_lla_tl = pd.read_csv(truth_lla_path)
            _passes_tl = detect_gs_passes(_df_lla_tl, gs_lat, gs_lon, gs_alt)
        if _df_truth_tl is not None:
            fig_tl = build_event_timeline_chart(
                _df_truth_tl, _df_ekf_tl, conjunctions, man_time, _passes_tl, _ecl_mask_tl
            )
            st.plotly_chart(fig_tl, width="stretch")
    except Exception as _e:
        st.warning(f"Timeline chart unavailable: {_e}")

# ------------------------------------------------------------
# Tab 2: Ground Tracks
# ------------------------------------------------------------
with tab2:
    st.markdown("### 🗺️ Ground Tracks (WGS84 LLA Coordinates)")
    
    if truth_lla_path.exists():
        df_truth_lla = pd.read_csv(truth_lla_path)
        times_list = df_truth_lla['time'].tolist()
        
        safe_idx = min(step_idx, len(df_truth_lla) - 1)
        curr_pt = df_truth_lla.iloc[safe_idx]

        
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
        
        st.plotly_chart(fig_gt, width="stretch")

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
            st.plotly_chart(fig_pos, width="stretch")
            
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
            st.plotly_chart(fig_vel, width="stretch")

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
                
                st.plotly_chart(fig_bp, width="stretch")

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
            st.plotly_chart(fig_pass, width="stretch")

# ------------------------------------------------------------
# Tab 6: Conjunction warnings
# ------------------------------------------------------------
with tab6:
    st.markdown("### ⚠️ Screened Debris Conjunction Warnings")
    
    if len(conjunctions) == 0:
        st.info(f"No objects detected within the {warning_threshold_km} km screening threshold.")
    else:
        # ── Avoidance Burn Advisor ────────────────────────────
        critical_conj = [c for c in conjunctions if c['probability_of_collision'] > 1e-5 or c['min_distance_m'] < 50_000]
        if critical_conj:
            c_top = critical_conj[0]
            dist_km_top = c_top['min_distance_m'] / 1000.0
            pc_top = c_top['probability_of_collision']
            st.markdown(f"""
<div class="avoidance-card">
  <h4>🛡️ Collision Avoidance Burn Advisor — Active</h4>
  <b style="color:#f43f5e">Critical Object:</b> {c_top['sat_name']} &nbsp;|&nbsp;
  Miss: <b>{dist_km_top:.1f} km</b> &nbsp;|&nbsp;
  Pc: <b>{pc_top:.2e}</b>
  <hr style="border-color:#3f065a; margin:8px 0">
""", unsafe_allow_html=True)
            try:
                burn_rec = compute_avoidance_burn_recommendation(
                    c_top['sat_position_m'], c_top['sat_velocity_m_s'],
                    c_top['tca_seconds'], dt
                )
                if burn_rec and burn_rec['dv_mag'] != 0.0:
                    comp_icon = {"radial": "⬆️", "in-track": "➡️", "cross-track": "↗️"}.get(burn_rec['component'], "🔧")
                    sign_str = "+" if burn_rec['dv_mag'] > 0 else ""
                    st.markdown(f"""
  <div class="avoidance-rec">{comp_icon} {sign_str}{burn_rec['dv_mag']:.2f} m/s {burn_rec['component'].capitalize()}</div>
  <div class="avoidance-detail">Projected position separation at TCA: <b style="color:#10b981">{burn_rec['projected_miss_km']:.1f} km</b></div>
  <div class="avoidance-detail" style="margin-top:4px;font-size:10px;">
    (Proxy computation using Keplerian forward-prop · for operational use, verify with high-fidelity tool)
  </div>
""", unsafe_allow_html=True)
                    # Apply Burn button
                    b1, b2, b3 = st.columns([1, 1, 3])
                    if b1.button("👉 Apply Burn to Planner", key="apply_burn_btn"):
                        comp = burn_rec['component']
                        dv = burn_rec['dv_mag']
                        if comp == "radial":
                            st.session_state['man_dvr'] = dv
                        elif comp == "in-track":
                            st.session_state['st_dvt'] = dv
                        elif comp == "cross-track":
                            st.session_state['st_dvn'] = dv
                        if man_time == 0.0:
                            st.session_state['man_time_val'] = max(10.0, c_top['tca_seconds'] * 0.5)
                        st.rerun()
                    b2.info(f"Burn at T+{c_top['tca_seconds'] * 0.5:.0f}s")
                else:
                    st.markdown('<div class="avoidance-detail">No beneficial burn found in ±2 m/s search window.</div>', unsafe_allow_html=True)
            except Exception as _av_e:
                st.markdown(f'<div class="avoidance-detail">Advisor unavailable: {_av_e}</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Conjunction Table ─────────────────────────────────
        st.markdown("#### 📋 Screened Object Table")
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


# ------------------------------------------------------------
# Tab 7: Orbital Analytics
# ------------------------------------------------------------
with tab7:
    st.markdown("### 📊 Orbital Analytics — Elements, Energy & Filter Convergence")
    
    if not truth_path.exists() or not ekf_path.exists():
        st.info("Run the simulation first to generate orbital analytics data.")
    else:
        try:
            _df_an_truth = pd.read_csv(truth_path)
            _df_an_ekf   = pd.read_csv(ekf_path)
            _df_an_cov   = pd.read_csv(covariance_path) if covariance_path.exists() else None

            # Compute Keplerian elements over time
            _times_an = _df_an_truth['time'].values
            _a_arr, _e_arr, _i_arr, _T_arr, _alt_arr = [], [], [], [], []
            _R_E = 6378.137
            for _row in _df_an_truth.itertuples():
                _els = state_to_elements(
                    [_row.x / 1000.0, _row.y / 1000.0, _row.z / 1000.0],
                    [_row.vx / 1000.0, _row.vy / 1000.0, _row.vz / 1000.0]
                )
                if _els:
                    _a_arr.append(_els['a_km'])
                    _e_arr.append(_els['e'])
                    _i_arr.append(_els['i_deg'])
                    _T_arr.append(_els['T_min'])
                    _alt_arr.append(_els['a_km'] - _R_E)
                else:
                    for _lst in [_a_arr, _e_arr, _i_arr, _T_arr, _alt_arr]:
                        _lst.append(None)

            # Filter innovation (3D position error over time)
            _pos_err = np.sqrt(
                (_df_an_ekf['x'].values - _df_an_truth['x'].values)**2 +
                (_df_an_ekf['y'].values - _df_an_truth['y'].values)**2 +
                (_df_an_ekf['z'].values - _df_an_truth['z'].values)**2
            )

            # Eclipse mask
            _ecl_mask_an = compute_eclipse_mask(_df_an_truth, epoch_utc)

            # ── Row 1: Elements charts ─────────────────────────────
            st.markdown("#### 🪐 Keplerian Elements Time History")
            _c71, _c72 = st.columns(2)

            with _c71:
                _fig_a = go.Figure()
                _fig_a.add_trace(go.Scatter(x=_times_an, y=_a_arr, mode='lines',
                                             line=dict(color='#06b6d4', width=2), name='SMA (km)'))
                _fig_a.update_layout(height=220, margin=dict(l=0,r=0,b=0,t=28),
                                      paper_bgcolor='rgba(2,5,15,1)', plot_bgcolor='rgba(5,10,25,0.8)',
                                      title=dict(text='Semi-major Axis a (km)', font=dict(color='#cbd5e1', size=12)),
                                      xaxis=dict(color='#64748b', gridcolor='#1e293b'),
                                      yaxis=dict(color='#64748b', gridcolor='#1e293b'),
                                      font=dict(color='#f3f4f6'), showlegend=False)
                st.plotly_chart(_fig_a, width="stretch")

                _fig_e = go.Figure()
                _fig_e.add_trace(go.Scatter(x=_times_an, y=_e_arr, mode='lines',
                                             line=dict(color='#a855f7', width=2), name='Eccentricity'))
                _fig_e.update_layout(height=220, margin=dict(l=0,r=0,b=0,t=28),
                                      paper_bgcolor='rgba(2,5,15,1)', plot_bgcolor='rgba(5,10,25,0.8)',
                                      title=dict(text='Eccentricity e', font=dict(color='#cbd5e1', size=12)),
                                      xaxis=dict(color='#64748b', gridcolor='#1e293b'),
                                      yaxis=dict(color='#64748b', gridcolor='#1e293b', tickformat='.5f'),
                                      font=dict(color='#f3f4f6'), showlegend=False)
                st.plotly_chart(_fig_e, width="stretch")

            with _c72:
                _fig_i = go.Figure()
                _fig_i.add_trace(go.Scatter(x=_times_an, y=_i_arr, mode='lines',
                                             line=dict(color='#f59e0b', width=2), name='Inclination (deg)'))
                _fig_i.update_layout(height=220, margin=dict(l=0,r=0,b=0,t=28),
                                      paper_bgcolor='rgba(2,5,15,1)', plot_bgcolor='rgba(5,10,25,0.8)',
                                      title=dict(text='Inclination i (°)', font=dict(color='#cbd5e1', size=12)),
                                      xaxis=dict(color='#64748b', gridcolor='#1e293b'),
                                      yaxis=dict(color='#64748b', gridcolor='#1e293b'),
                                      font=dict(color='#f3f4f6'), showlegend=False)
                st.plotly_chart(_fig_i, width="stretch")

                _fig_T = go.Figure()
                _fig_T.add_trace(go.Scatter(x=_times_an, y=_T_arr, mode='lines',
                                             line=dict(color='#10b981', width=2), name='Period (min)'))
                _fig_T.update_layout(height=220, margin=dict(l=0,r=0,b=0,t=28),
                                      paper_bgcolor='rgba(2,5,15,1)', plot_bgcolor='rgba(5,10,25,0.8)',
                                      title=dict(text='Orbital Period T (min)', font=dict(color='#cbd5e1', size=12)),
                                      xaxis=dict(color='#64748b', gridcolor='#1e293b'),
                                      yaxis=dict(color='#64748b', gridcolor='#1e293b'),
                                      font=dict(color='#f3f4f6'), showlegend=False)
                st.plotly_chart(_fig_T, width="stretch")

            # ── Row 2: Filter innovation + Eclipse ────────────────
            st.markdown("#### 🔬 Filter Convergence & Eclipse Profile")
            _c73, _c74 = st.columns(2)

            with _c73:
                _fig_err = go.Figure()
                _fig_err.add_trace(go.Scatter(
                    x=_times_an, y=_pos_err,
                    mode='lines', line=dict(color='#f43f5e', width=2), fill='tozeroy',
                    fillcolor='rgba(244,63,94,0.08)', name='Position Error (m)'
                ))
                _fig_err.update_layout(height=220, margin=dict(l=0,r=0,b=0,t=28),
                                        paper_bgcolor='rgba(2,5,15,1)', plot_bgcolor='rgba(5,10,25,0.8)',
                                        title=dict(text=f'Filter Innovation — {filter_choice} 3D Position Error (m)',
                                                   font=dict(color='#cbd5e1', size=12)),
                                        xaxis=dict(title='Time (s)', color='#64748b', gridcolor='#1e293b'),
                                        yaxis=dict(color='#64748b', gridcolor='#1e293b'),
                                        font=dict(color='#f3f4f6'), showlegend=False)
                st.plotly_chart(_fig_err, width="stretch")

            with _c74:
                _ecl_vals = _ecl_mask_an.astype(float)
                _fig_ecl = go.Figure()
                _fig_ecl.add_trace(go.Scatter(
                    x=_times_an, y=_ecl_vals,
                    mode='lines', line=dict(color='#64748b', width=1.5),
                    fill='tozeroy', fillcolor='rgba(30,41,59,0.5)', name='Eclipse'
                ))
                _fig_ecl.update_layout(height=220, margin=dict(l=0,r=0,b=0,t=28),
                                        paper_bgcolor='rgba(2,5,15,1)', plot_bgcolor='rgba(5,10,25,0.8)',
                                        title=dict(text=f'Eclipse Profile (1=shadow, frac={_eclipse_frac_str})',
                                                   font=dict(color='#cbd5e1', size=12)),
                                        xaxis=dict(title='Time (s)', color='#64748b', gridcolor='#1e293b'),
                                        yaxis=dict(color='#64748b', gridcolor='#1e293b', range=[-0.1, 1.1]),
                                        font=dict(color='#f3f4f6'), showlegend=False)
                st.plotly_chart(_fig_ecl, width="stretch")

            # ── Covariance trace ──────────────────────────────────
            if _df_an_cov is not None:
                st.markdown("#### 📐 Covariance Diagonal (Position σ) Over Time")
                _fig_cov = go.Figure()
                _fig_cov.add_trace(go.Scatter(x=_df_an_cov['time'],
                                               y=np.sqrt(_df_an_cov['p_xx']),
                                               mode='lines', line=dict(color='#06b6d4', width=1.5), name='σ_x (m)'))
                _fig_cov.add_trace(go.Scatter(x=_df_an_cov['time'],
                                               y=np.sqrt(_df_an_cov['p_yy']),
                                               mode='lines', line=dict(color='#a855f7', width=1.5), name='σ_y (m)'))
                _fig_cov.add_trace(go.Scatter(x=_df_an_cov['time'],
                                               y=np.sqrt(_df_an_cov['p_zz']),
                                               mode='lines', line=dict(color='#f59e0b', width=1.5), name='σ_z (m)'))
                _fig_cov.update_layout(height=220, margin=dict(l=0,r=0,b=0,t=28),
                                        paper_bgcolor='rgba(2,5,15,1)', plot_bgcolor='rgba(5,10,25,0.8)',
                                        title=dict(text='Position Covariance σ (1σ, metres)',
                                                   font=dict(color='#cbd5e1', size=12)),
                                        xaxis=dict(title='Time (s)', color='#64748b', gridcolor='#1e293b'),
                                        yaxis=dict(color='#64748b', gridcolor='#1e293b'),
                                        legend=dict(bgcolor='rgba(3,7,18,0.75)', font=dict(color='#cbd5e1', size=10)),
                                        font=dict(color='#f3f4f6'))
                st.plotly_chart(_fig_cov, width="stretch")

        except Exception as _tab7_err:
            st.error(f"Orbital analytics error: {_tab7_err}")
            import traceback
            st.code(traceback.format_exc())


# ─────────────────────────────────────────────────────────────
# Auto-play loop – trigger rerun after brief sleep
# ─────────────────────────────────────────────────────────────
if play_mode:
    time.sleep(0.08)
    st.rerun()
