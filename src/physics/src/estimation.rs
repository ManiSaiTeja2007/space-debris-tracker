use nalgebra::{DMatrix, DVector, Matrix6, Vector3, Vector6, Matrix3, Matrix3x6, Matrix6x3};
use crate::state::OrbitalState;
use crate::propagator::propagate;

// Compute the Jacobian H and residual vector b numerically.
// The state vector x0 is [x, y, z, vx, vy, vz]
fn compute_jacobian_and_residuals(
    x0: &Vector6<f64>,
    obs_positions: &[Vector3<f64>],
    dt: f64,
    steps: usize,
) -> (DMatrix<f64>, DVector<f64>) {
    let state0 = OrbitalState::new(
        Vector3::new(x0[0], x0[1], x0[2]),
        Vector3::new(x0[3], x0[4], x0[5]),
    );
    let traj_pred = propagate(&state0, dt, steps);
    
    // Residuals vector b (size 3 * steps)
    let mut b = DVector::zeros(3 * steps);
    for i in 0..steps {
        let r_obs = obs_positions[i];
        let r_pred = traj_pred[i].r;
        let diff = r_obs - r_pred;
        b[3 * i] = diff[0];
        b[3 * i + 1] = diff[1];
        b[3 * i + 2] = diff[2];
    }
    
    // Jacobian H (size 3 * steps x 6)
    let mut h = DMatrix::zeros(3 * steps, 6);
    
    let dp = 1.0;
    let dv = 1e-4;
    let epsilons = [dp, dp, dp, dv, dv, dv];
    
    for j in 0..6 {
        let mut x_perturbed = *x0;
        x_perturbed[j] += epsilons[j];
        
        let state_pert = OrbitalState::new(
            Vector3::new(x_perturbed[0], x_perturbed[1], x_perturbed[2]),
            Vector3::new(x_perturbed[3], x_perturbed[4], x_perturbed[5]),
        );
        let traj_pert = propagate(&state_pert, dt, steps);
        
        for i in 0..steps {
            let dr = (traj_pert[i].r - traj_pred[i].r) / epsilons[j];
            h[(3 * i, j)] = dr[0];
            h[(3 * i + 1, j)] = dr[1];
            h[(3 * i + 2, j)] = dr[2];
        }
    }
    
    (h, b)
}

pub fn fit_orbit(
    initial_guess: &Vector6<f64>,
    obs_positions: &[Vector3<f64>],
    dt: f64,
    steps: usize,
    max_iter: usize,
    tol: f64,
) -> Vector6<f64> {
    let mut x = *initial_guess;
    
    for iter in 1..=max_iter {
        let (h, b) = compute_jacobian_and_residuals(&x, obs_positions, dt, steps);
        
        // Solve Normal Equations: (H^T * H) * dx = H^T * b
        let h_t = h.transpose();
        let lhs = &h_t * &h;
        let rhs = &h_t * &b;
        
        // Solve using LU decomposition
        let decomp = lhs.lu();
        let dx = match decomp.solve(&rhs) {
            Some(sol) => sol,
            None => {
                println!("[WARNING] Singular matrix in LeastSquares. Aborting fitting loop.");
                break;
            }
        };
        
        let pos_step = Vector3::new(dx[0], dx[1], dx[2]).norm();
        let vel_step = Vector3::new(dx[3], dx[4], dx[5]).norm();
        
        x += dx;
        
        println!(
            "LeastSquares Iter {}: |dx_pos| = {:.4} m, |dx_vel| = {:.6} m/s",
            iter, pos_step, vel_step
        );
        
        if pos_step < tol && vel_step < (tol * 1e-4) {
            println!("LeastSquares: Converged successfully at iteration {}.", iter);
            break;
        }
    }
    
    x
}

/// Run an Extended Kalman Filter (EKF) over position observations.
/// Returns the list of estimated states and covariances at each step.
pub fn run_ekf(
    initial_guess: &Vector6<f64>,
    initial_covariance: &Matrix6<f64>,
    obs_positions: &[Vector3<f64>],
    dt: f64,
    steps: usize,
    sigma_r: f64,
) -> (Vec<Vector6<f64>>, Vec<Matrix6<f64>>) {
    let mut x = *initial_guess;
    let mut p = *initial_covariance;
    
    let mut est_states = Vec::with_capacity(steps);
    let mut est_covariances = Vec::with_capacity(steps);
    
    // Measurement noise covariance R (3x3 position only)
    let r_cov = Matrix3::from_diagonal(&Vector3::repeat(sigma_r * sigma_r));
    
    // Process noise covariance Q (6x6)
    let q_cov = Matrix6::from_diagonal(&Vector6::new(
        0.1 * 0.1, 0.1 * 0.1, 0.1 * 0.1,
        1e-4 * 1e-4, 1e-4 * 1e-4, 1e-4 * 1e-4,
    ));
    
    for i in 0..steps {
        // --- 1. PREDICT STEP ---
        let state_prev = OrbitalState::new(
            Vector3::new(x[0], x[1], x[2]),
            Vector3::new(x[3], x[4], x[5]),
        );
        let traj_pred = propagate(&state_prev, dt, 1);
        let x_pred = Vector6::new(
            traj_pred[0].r[0], traj_pred[0].r[1], traj_pred[0].r[2],
            traj_pred[0].v[0], traj_pred[0].v[1], traj_pred[0].v[2],
        );
        
        // Compute 1-step STM Phi numerically to predict covariance
        let mut stm = Matrix6::zeros();
        let dp = 1.0;
        let dv = 1e-4;
        let epsilons = [dp, dp, dp, dv, dv, dv];
        
        for j in 0..6 {
            let mut x_pert = x;
            x_pert[j] += epsilons[j];
            let state_pert = OrbitalState::new(
                Vector3::new(x_pert[0], x_pert[1], x_pert[2]),
                Vector3::new(x_pert[3], x_pert[4], x_pert[5]),
            );
            let traj_pert = propagate(&state_pert, dt, 1);
            let x_pert_pred = Vector6::new(
                traj_pert[0].r[0], traj_pert[0].r[1], traj_pert[0].r[2],
                traj_pert[0].v[0], traj_pert[0].v[1], traj_pert[0].v[2],
            );
            let col = (x_pert_pred - x_pred) / epsilons[j];
            stm.set_column(j, &col);
        }
        
        // P_pred = Phi * P_prev * Phi^T + Q
        let p_pred = &stm * p * stm.transpose() + &q_cov;
        
        // --- 2. UPDATE STEP ---
        let y_obs = obs_positions[i];
        let y_pred = Vector3::new(x_pred[0], x_pred[1], x_pred[2]);
        let residual = y_obs - y_pred;
        
        // Innovation covariance: S = H * P_pred * H^T + R
        let p_pred_pos = p_pred.fixed_view::<3, 3>(0, 0);
        let s_cov = p_pred_pos + &r_cov;
        
        // Solve for Kalman Gain: K = P_pred * H^T * S^-1
        let h_p_pred = p_pred.fixed_view::<3, 6>(0, 0);
        let s_decomp = s_cov.lu();
        
        let mut k_t = Matrix6x3::zeros();
        for col_idx in 0..6 {
            let rhs_vec = Vector3::new(h_p_pred[(0, col_idx)], h_p_pred[(1, col_idx)], h_p_pred[(2, col_idx)]);
            if let Some(gain_col) = s_decomp.solve(&rhs_vec) {
                k_t.set_row(col_idx, &gain_col.transpose());
            }
        }
        let k_gain = k_t; // 6x3 Kalman Gain
        
        // State update: x = x_pred + K * residual
        x = x_pred + &k_gain * residual;
        
        // Covariance update: P = (I - K * H) * P_pred
        let mut eye_minus_kh = Matrix6::identity();
        for col_idx in 0..3 {
            for row_idx in 0..6 {
                eye_minus_kh[(row_idx, col_idx)] -= k_gain[(row_idx, col_idx)];
            }
        }
        p = &eye_minus_kh * &p_pred;
        
        est_states.push(x);
        est_covariances.push(p);
    }
    
    (est_states, est_covariances)
}
