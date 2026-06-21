use nalgebra::Vector3;
use rand::thread_rng;
use rand_distr::{Distribution, Normal};
use crate::state::OrbitalState;

pub fn gaussian_noise(sigma_r: f64, sigma_v: f64) -> (Vector3<f64>, Vector3<f64>) {
    let mut rng = thread_rng();
    let norm_r = Normal::new(0.0, sigma_r).unwrap();
    let norm_v = Normal::new(0.0, sigma_v).unwrap();
    
    let dr = Vector3::new(
        norm_r.sample(&mut rng),
        norm_r.sample(&mut rng),
        norm_r.sample(&mut rng),
    );
    let dv = Vector3::new(
        norm_v.sample(&mut rng),
        norm_v.sample(&mut rng),
        norm_v.sample(&mut rng),
    );
    
    (dr, dv)
}

pub fn observe_state(state: &OrbitalState, sigma_r: f64, sigma_v: f64) -> OrbitalState {
    let (dr, dv) = gaussian_noise(sigma_r, sigma_v);
    OrbitalState::new(state.r + dr, state.v + dv)
}
