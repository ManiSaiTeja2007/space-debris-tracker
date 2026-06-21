use nalgebra::{Matrix6, Matrix3, Vector3, Vector6, Matrix6x3, Matrix3x6};
use crate::state::OrbitalState;
use crate::propagator::propagate_from;

/// Run the Unscented Kalman Filter (UKF) over position observations.
/// Returns the list of estimated states and covariances at each step.
pub fn run_ukf(
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
    
    // UKF parameters
    let n = 6.0;
    let lambda = -3.0; // Standard choice lambda = 3 - N
    let n_plus_lambda = n + lambda; // 3.0
    
    // Weights
    let w_m0 = lambda / n_plus_lambda; // -1.0
    let w_c0 = w_m0 + 2.0; // w_m0 + (1 - alpha^2 + beta) with alpha=1, beta=2 => 1.0
    let w_i = 1.0 / (2.0 * n_plus_lambda); // 1 / 6.0
    
    for i in 0..steps {
        let t_curr = (i as f64) * dt;
        
        // --- 1. GENERATE SIGMA POINTS ---
        // Calculate Cholesky square root: L = sqrt((N + lambda) * P)
        let scale_p = n_plus_lambda * p;
        let l_mat = match scale_p.cholesky() {
            Some(c) => c.l(),
            None => {
                // If Cholesky fails due to non-positive definiteness, add perturbation
                let mut scale_p_perturbed = scale_p;
                for j in 0..6 {
                    scale_p_perturbed[(j, j)] += 1e-5;
                }
                match scale_p_perturbed.cholesky() {
                    Some(c) => c.l(),
                    None => {
                        // Fallback to identity scale
                        Matrix6::identity()
                    }
                }
            }
        };
        
        let mut sigma_points = Vec::with_capacity(13);
        // chi_0
        sigma_points.push(x);
        // chi_i (i = 1..6)
        for col_idx in 0..6 {
            let col = l_mat.column(col_idx);
            sigma_points.push(x + col);
        }
        // chi_i+6 (i = 1..6)
        for col_idx in 0..6 {
            let col = l_mat.column(col_idx);
            sigma_points.push(x - col);
        }
        
        // --- 2. PROPAGATE SIGMA POINTS ---
        let mut propagated_sigmas = Vec::with_capacity(13);
        for sig in &sigma_points {
            let state_sig = OrbitalState::new(
                Vector3::new(sig[0], sig[1], sig[2]),
                Vector3::new(sig[3], sig[4], sig[5]),
            );
            let traj_sig = propagate_from(&state_sig, dt, 1, t_curr);
            let sig_pred = Vector6::new(
                traj_sig[0].r[0], traj_sig[0].r[1], traj_sig[0].r[2],
                traj_sig[0].v[0], traj_sig[0].v[1], traj_sig[0].v[2],
            );
            propagated_sigmas.push(sig_pred);
        }
        
        // --- 3. PREDICTED STATE MEAN AND COVARIANCE ---
        let mut x_pred = w_m0 * propagated_sigmas[0];
        for k in 1..13 {
            x_pred += w_i * propagated_sigmas[k];
        }
        
        let diff0 = propagated_sigmas[0] - x_pred;
        let mut p_pred = w_c0 * (&diff0 * &diff0.transpose());
        for k in 1..13 {
            let diff_k = propagated_sigmas[k] - x_pred;
            p_pred += w_i * (&diff_k * &diff_k.transpose());
        }
        p_pred += &q_cov;
        
        // --- 4. PREDICTED MEASUREMENT MEAN AND COVARIANCES ---
        // Measurement model: h(x) is position coordinates (first 3 elements)
        let mut meas_sigmas = Vec::with_capacity(13);
        for sig in &propagated_sigmas {
            meas_sigmas.push(Vector3::new(sig[0], sig[1], sig[2]));
        }
        
        let mut y_pred = w_m0 * meas_sigmas[0];
        for k in 1..13 {
            y_pred += w_i * meas_sigmas[k];
        }
        
        let diff_y0 = meas_sigmas[0] - y_pred;
        let mut p_yy = w_c0 * (&diff_y0 * &diff_y0.transpose());
        for k in 1..13 {
            let diff_yk = meas_sigmas[k] - y_pred;
            p_yy += w_i * (&diff_yk * &diff_yk.transpose());
        }
        p_yy += &r_cov;
        
        // Cross-covariance P_xy
        let mut p_xy = w_c0 * (&diff0 * &diff_y0.transpose());
        for k in 1..13 {
            let diff_k = propagated_sigmas[k] - x_pred;
            let diff_yk = meas_sigmas[k] - y_pred;
            p_xy += w_i * (&diff_k * &diff_yk.transpose());
        }
        
        // --- 5. MEASUREMENT UPDATE ---
        let y_obs = obs_positions[i];
        let residual = y_obs - y_pred;
        
        // Solve for Kalman Gain: K = P_xy * P_yy^-1
        let p_yy_decomp = p_yy.lu();
        
        let mut k_t = Matrix6x3::zeros();
        for row_idx in 0..6 {
            let rhs_vec = Vector3::new(p_xy[(row_idx, 0)], p_xy[(row_idx, 1)], p_xy[(row_idx, 2)]);
            if let Some(gain_row) = p_yy_decomp.solve(&rhs_vec) {
                k_t.set_row(row_idx, &gain_row.transpose());
            }
        }
        let k_gain = k_t; // 6x3 Kalman Gain
        
        // State update
        x = x_pred + &k_gain * residual;
        
        // Covariance update
        p = p_pred - &k_gain * &p_yy * &k_gain.transpose();
        
        est_states.push(x);
        est_covariances.push(p);
    }
    
    (est_states, est_covariances)
}
