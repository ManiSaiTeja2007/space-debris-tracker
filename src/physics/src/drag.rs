use nalgebra::Vector3;
use crate::constants::{R_EARTH, OMEGA_EARTH, CD, A_OVER_M, RHO_0, H_0, H_SCALE};

pub fn accel_drag(r: &Vector3<f64>, v: &Vector3<f64>) -> Vector3<f64> {
    let r_norm = r.norm();
    let altitude = r_norm - R_EARTH;
    
    // Exponential atmospheric density model
    let density = RHO_0 * (- (altitude - H_0) / H_SCALE).exp();
    
    // Velocity of the atmosphere due to Earth's rotation: w x r
    // w = [0, 0, OMEGA_EARTH]
    let v_atm = Vector3::new(-OMEGA_EARTH * r[1], OMEGA_EARTH * r[0], 0.0);
    
    // Relative velocity: v_rel = v - v_atm
    let v_rel = v - v_atm;
    let v_rel_norm = v_rel.norm();
    
    // Drag acceleration: a_drag = -0.5 * rho * Cd * (A/m) * v_rel_norm * v_rel
    -0.5 * density * CD * A_OVER_M * v_rel_norm * v_rel
}
