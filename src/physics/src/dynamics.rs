use nalgebra::Vector3;
use crate::gravity::accel_gravity;
use crate::j2::{accel_j2, accel_j3, accel_j4};
use crate::drag::accel_drag;
use crate::third_body::third_body_perturbation;
use crate::srp::accel_srp;

// Returns (velocity derivative, acceleration derivative) at time t (seconds since epoch)
pub fn state_derivative(r: &Vector3<f64>, v: &Vector3<f64>, t: f64) -> (Vector3<f64>, Vector3<f64>) {
    let a = accel_gravity(r) 
        + accel_j2(r) 
        + accel_j3(r) 
        + accel_j4(r) 
        + accel_drag(r, v)
        + third_body_perturbation(r, t)
        + accel_srp(r, t);
    (*v, a)
}

