use nalgebra::Vector3;
use crate::constants::MU_EARTH;

pub fn accel_gravity(r: &Vector3<f64>) -> Vector3<f64> {
    let r_norm = r.norm();
    -MU_EARTH * r / r_norm.powi(3)
}
