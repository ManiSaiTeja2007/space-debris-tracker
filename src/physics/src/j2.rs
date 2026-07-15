use nalgebra::Vector3;
use crate::constants::{MU_EARTH, R_EARTH, J2_EARTH, J3_EARTH, J4_EARTH};

// J2 acceleration perturbation
pub fn accel_j2(r: &Vector3<f64>) -> Vector3<f64> {
    let x = r[0];
    let y = r[1];
    let z = r[2];
    
    let r_norm = r.norm();
    let r2 = r_norm.powi(2);
    let z2 = z.powi(2);
    
    let factor = 1.5 * J2_EARTH * MU_EARTH * R_EARTH.powi(2) / r_norm.powi(5);
    
    let ax = factor * x * (5.0 * z2 / r2 - 1.0);
    let ay = factor * y * (5.0 * z2 / r2 - 1.0);
    let az = factor * z * (5.0 * z2 / r2 - 3.0);
    
    Vector3::new(ax, ay, az)
}

// J3 acceleration perturbation
pub fn accel_j3(r: &Vector3<f64>) -> Vector3<f64> {
    let x = r[0];
    let y = r[1];
    let z = r[2];
    
    let r_norm = r.norm();
    let r_inv = 1.0 / r_norm;
    let z_r = z * r_inv;
    let z_r_2 = z_r.powi(2);
    let z_r_3 = z_r.powi(3);
    
    let factor = -2.5 * J3_EARTH * MU_EARTH * R_EARTH.powi(3) / r_norm.powi(7);
    
    let ax = factor * x * (3.0 * z_r - 7.0 * z_r_3);
    let ay = factor * y * (3.0 * z_r - 7.0 * z_r_3);
    let az = -0.5 * J3_EARTH * (MU_EARTH * R_EARTH.powi(3) / r_norm.powi(5)) * (30.0 * z_r_2 - 35.0 * z_r_2 * z_r_2 - 3.0);
    
    Vector3::new(ax, ay, az)
}

// J4 acceleration perturbation
pub fn accel_j4(r: &Vector3<f64>) -> Vector3<f64> {
    let x = r[0];
    let y = r[1];
    let z = r[2];
    
    let r_norm = r.norm();
    let r_inv = 1.0 / r_norm;
    let z_r = z * r_inv;
    let z_r_2 = z_r.powi(2);
    let z_r_4 = z_r.powi(4);
    
    let factor = 0.625 * J4_EARTH * MU_EARTH * R_EARTH.powi(4) / r_norm.powi(7);
    
    let ax = factor * x * (63.0 * z_r_4 - 42.0 * z_r_2 + 3.0);
    let ay = factor * y * (63.0 * z_r_4 - 42.0 * z_r_2 + 3.0);
    let az = factor * z * (63.0 * z_r_4 - 70.0 * z_r_2 + 15.0);
    
    Vector3::new(ax, ay, az)
}
