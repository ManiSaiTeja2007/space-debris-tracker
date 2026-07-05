use crate::state::OrbitalState;
use crate::rk4::rk4_step;
use crate::dynamics::state_derivative;
use crate::rk45::propagate_rk45;
use nalgebra::{Matrix6, Vector3, Vector6};

/// Propagate the orbital state starting from t=0.0.
pub fn propagate(state0: &OrbitalState, dt: f64, steps: usize) -> Vec<OrbitalState> {
    propagate_from(state0, dt, steps, 0.0)
}

/// Propagate the orbital state starting from an arbitrary time t_start.
pub fn propagate_from(state0: &OrbitalState, dt: f64, steps: usize, t_start: f64) -> Vec<OrbitalState> {
    let mut r = state0.r;
    let mut v = state0.v;
    let mut trajectory = Vec::with_capacity(steps);
    
    for i in 0..steps {
        let t = t_start + (i as f64) * dt;
        let (r_new, v_new) = rk4_step(|r_curr, v_curr| state_derivative(r_curr, v_curr, t), &r, &v, dt);
        r = r_new;
        v = v_new;
        trajectory.push(OrbitalState::new(r, v));
    }
    
    trajectory
}

/// Propagate state along with its 6x6 covariance matrix starting from t=0.0.
pub fn propagate_with_covariance(
    state0: &OrbitalState,
    p0: &Matrix6<f64>,
    dt: f64,
    steps: usize,
) -> (Vec<OrbitalState>, Vec<Matrix6<f64>>) {
    propagate_with_covariance_from(state0, p0, dt, steps, 0.0)
}

/// Propagate state along with its 6x6 covariance matrix starting from t_start.
pub fn propagate_with_covariance_from(
    state0: &OrbitalState,
    p0: &Matrix6<f64>,
    dt: f64,
    steps: usize,
    t_start: f64,
) -> (Vec<OrbitalState>, Vec<Matrix6<f64>>) {
    // 1. Propagate main trajectory
    let traj_main = propagate_from(state0, dt, steps, t_start);
    
    // 2. Compute perturbed trajectories to construct the STM column-by-column
    let x0 = Vector6::new(
        state0.r[0], state0.r[1], state0.r[2],
        state0.v[0], state0.v[1], state0.v[2],
    );
    
    let dp = 1.0;
    let dv = 1e-4;
    let epsilons = [dp, dp, dp, dv, dv, dv];
    
    let mut perturbed_trajectories = Vec::with_capacity(6);
    
    for j in 0..6 {
        let mut x0_pert = x0;
        x0_pert[j] += epsilons[j];
        
        let state_pert = OrbitalState::new(
            Vector3::new(x0_pert[0], x0_pert[1], x0_pert[2]),
            Vector3::new(x0_pert[3], x0_pert[4], x0_pert[5]),
        );
        perturbed_trajectories.push(propagate_from(&state_pert, dt, steps, t_start));
    }
    
    // 3. Reconstruct STM and propagate covariance at each step
    let mut covariances = Vec::with_capacity(steps);
    
    for i in 0..steps {
        let mut stm = Matrix6::zeros();
        let x_main = Vector6::new(
            traj_main[i].r[0], traj_main[i].r[1], traj_main[i].r[2],
            traj_main[i].v[0], traj_main[i].v[1], traj_main[i].v[2],
        );
        
        for j in 0..6 {
            let traj_pert = &perturbed_trajectories[j];
            let x_pert = Vector6::new(
                traj_pert[i].r[0], traj_pert[i].r[1], traj_pert[i].r[2],
                traj_pert[i].v[0], traj_pert[i].v[1], traj_pert[i].v[2],
            );
            // STM column j = (x_pert - x_main) / epsilon
            let col = (x_pert - x_main) / epsilons[j];
            stm.set_column(j, &col);
        }
        
        // P(t) = Phi * P0 * Phi^T
        let p_t = &stm * p0 * stm.transpose();
        covariances.push(p_t);
    }
    
    (traj_main, covariances)
}

/// Propagate using adaptive RK45 (outputs same uniform-step trajectory format).
pub fn propagate_adaptive(state0: &OrbitalState, dt: f64, steps: usize, t_start: f64) -> Vec<OrbitalState> {
    let f = |r: &Vector3<f64>, v: &Vector3<f64>, t: f64| state_derivative(r, v, t);
    let result = propagate_rk45(&f, &state0.r, &state0.v, t_start, dt, steps, 1.0, 1e-9);
    result.into_iter().map(|(r, v)| OrbitalState::new(r, v)).collect()
}
