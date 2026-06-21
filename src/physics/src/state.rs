use nalgebra::Vector3;
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrbitalState {
    pub r: Vector3<f64>, // Position [x, y, z] in meters
    pub v: Vector3<f64>, // Velocity [vx, vy, vz] in m/s
}

impl OrbitalState {
    pub fn new(r: Vector3<f64>, v: Vector3<f64>) -> Self {
        OrbitalState { r, v }
    }
}
