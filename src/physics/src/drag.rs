use nalgebra::Vector3;
use crate::constants::{R_EARTH, OMEGA_EARTH, CD, A_OVER_M};

// 5-layer piecewise atmosphere: (h_base_m, rho_0 kg/m³, H_scale_m)
const ATMO_TABLE: &[(f64, f64, f64)] = &[
    (100_000.0, 5.604e-7,  5_877.0),
    (200_000.0, 2.789e-9,  7_714.0),
    (300_000.0, 1.916e-11, 8_766.0),
    (450_000.0, 1.171e-12, 9_473.0),
    (600_000.0, 5.245e-13, 12_636.0),
];

pub fn atmosphere_density(altitude_m: f64) -> f64 {
    // Select layer bracket: find the highest base altitude <= altitude_m
    let mut layer = &ATMO_TABLE[ATMO_TABLE.len() - 1];
    for window in ATMO_TABLE.windows(2) {
        if altitude_m < window[1].0 {
            layer = &window[0];
            break;
        }
    }
    let (h_base, rho_0, h_scale) = *layer;
    rho_0 * (-(altitude_m - h_base) / h_scale).exp()
}

pub fn accel_drag(r: &Vector3<f64>, v: &Vector3<f64>) -> Vector3<f64> {
    let r_norm = r.norm();
    let altitude = r_norm - R_EARTH;

    // Drag is negligible below 80 km and above 1200 km
    if altitude < 80_000.0 || altitude > 1_200_000.0 {
        return Vector3::zeros();
    }

    let density = atmosphere_density(altitude);

    // Velocity of atmosphere rotating with Earth: ω × r
    let v_atm = Vector3::new(-OMEGA_EARTH * r[1], OMEGA_EARTH * r[0], 0.0);

    // Relative velocity of satellite w.r.t. atmosphere
    let v_rel = v - v_atm;
    let v_rel_norm = v_rel.norm();
    if v_rel_norm < 1e-10 {
        return Vector3::zeros();
    }

    // Drag acceleration: a_drag = -0.5 * ρ * Cd * (A/m) * |v_rel| * v_rel
    -0.5 * density * CD * A_OVER_M * v_rel_norm * v_rel
}
