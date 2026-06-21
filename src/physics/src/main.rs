mod constants;
mod state;
mod gravity;
mod j2;
mod drag;
mod third_body;
mod srp;
mod dynamics;
mod rk4;
mod propagator;
mod noise;
mod estimation;
mod ukf;
mod conjunction;

use std::env;
use std::fs::{self, File};
use std::path::Path;
use nalgebra::{Vector3, Vector6, Matrix6};
use state::OrbitalState;
use constants::{R_EARTH, MU_EARTH};
use propagator::{propagate_from, propagate_with_covariance_from};
use noise::observe_state;
use estimation::{fit_orbit, run_ekf};
use rk4::rk4_step;
use serde::Serialize;
use serde_json::Value;
use chrono::{DateTime, Utc};

#[derive(Serialize)]
struct EstimationMetrics {
    true_initial_state: Vec<f64>,
    estimated_initial_state: Vec<f64>,
    initial_position_error_m: f64,
    initial_velocity_error_m_s: f64,
    trajectory_position_rmse_m: f64,
    trajectory_velocity_rmse_m_s: f64,
    ekf_final_position_error_m: f64,
    ekf_final_velocity_error_m_s: f64,
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("[ERROR] Repo root argument not provided");
        std::process::exit(1);
    }
    
    let repo_root = &args[1];
    let enable_noise = args.len() >= 3 && args[2] == "1";
    let sigma_r = if args.len() >= 4 { args[3].parse::<f64>().unwrap_or(50.0) } else { 50.0 };
    let sigma_v = if args.len() >= 5 { args[4].parse::<f64>().unwrap_or(0.05) } else { 0.05 };
    
    // Parse custom state coordinates
    let mut true_state0 = {
        let altitude = 400e3;
        let r0_mag = R_EARTH + altitude;
        let v0_mag = (MU_EARTH / r0_mag).sqrt();
        OrbitalState::new(
            Vector3::new(r0_mag, 0.0, 0.0),
            Vector3::new(0.0, v0_mag, 0.0),
        )
    };

    if args.len() >= 11 {
        let px = args[5].parse::<f64>().expect("Invalid px");
        let py = args[6].parse::<f64>().expect("Invalid py");
        let pz = args[7].parse::<f64>().expect("Invalid pz");
        let vx = args[8].parse::<f64>().expect("Invalid vx");
        let vy = args[9].parse::<f64>().expect("Invalid vy");
        let vz = args[10].parse::<f64>().expect("Invalid vz");
        true_state0 = OrbitalState::new(
            Vector3::new(px, py, pz),
            Vector3::new(vx, vy, vz),
        );
        println!(
            "Using custom initial state: pos=[{:.3}, {:.3}, {:.3}] m, vel=[{:.3}, {:.3}, {:.3}] m/s",
            px, py, pz, vx, vy, vz
        );
    } else {
        println!(
            "Using default ISS orbit: pos=[{:.3}, {:.3}, {:.3}] m, vel=[{:.3}, {:.3}, {:.3}] m/s",
            true_state0.r[0], true_state0.r[1], true_state0.r[2],
            true_state0.v[0], true_state0.v[1], true_state0.v[2]
        );
    }

    // Parse filter choice and maneuver parameters
    let filter_choice = if args.len() >= 12 { args[11].as_str() } else { "ekf" };
    let man_time = if args.len() >= 13 { args[12].parse::<f64>().unwrap_or(0.0) } else { 0.0 };
    let man_dv_r = if args.len() >= 14 { args[13].parse::<f64>().unwrap_or(0.0) } else { 0.0 };
    let man_dv_t = if args.len() >= 15 { args[14].parse::<f64>().unwrap_or(0.0) } else { 0.0 };
    let man_dv_n = if args.len() >= 16 { args[15].parse::<f64>().unwrap_or(0.0) } else { 0.0 };
    let dv_vector = Vector3::new(man_dv_r, man_dv_t, man_dv_n);

    let out_dir = Path::new(repo_root).join("data").join("generated");
    fs::create_dir_all(&out_dir).expect("Failed to create output directory");
    
    // Read time contract from time_reference.json
    let time_ref_path = Path::new(repo_root).join("time_reference.json");
    let mut dt = 10.0;
    let mut steps = 540;
    let mut epoch_utc = Utc::now();
    
    if time_ref_path.exists() {
        if let Ok(content) = fs::read_to_string(&time_ref_path) {
            if let Ok(v) = serde_json::from_str::<Value>(&content) {
                if let Some(d) = v["dt_seconds"].as_f64() { dt = d; }
                if let Some(s) = v["steps"].as_u64() { steps = s as usize; }
                if let Some(epoch_str) = v["epoch_utc"].as_str() {
                    if let Ok(dt_parsed) = DateTime::parse_from_rfc3339(epoch_str) {
                        epoch_utc = dt_parsed.with_timezone(&Utc);
                    }
                }
                println!(
                    "Loaded time contract: dt = {} s, steps = {}, epoch = {}",
                    dt, steps, epoch_utc.to_rfc3339()
                );
            }
        }
    }
    
    // 1. Simulate true orbit (with maneuver if scheduled)
    println!("Simulating true orbit...");
    let traj_truth = propagate_with_maneuver(&true_state0, dt, steps, man_time, &dv_vector);
    
    // 2. Generate Noisy Observations
    println!("Generating observations (noise: sigma_r = {} m, sigma_v = {} m/s)...", sigma_r, sigma_v);
    let mut traj_observed = Vec::with_capacity(steps);
    for s in &traj_truth {
        if enable_noise {
            traj_observed.push(observe_state(s, sigma_r, sigma_v));
        } else {
            traj_observed.push(s.clone());
        }
    }
    
    // 3. Run Orbit Determination (Batch Least Squares)
    println!("Running Orbit Determination...");
    let first_obs = &traj_observed[0];
    let init_guess = Vector6::new(
        first_obs.r[0], first_obs.r[1], first_obs.r[2],
        first_obs.v[0], first_obs.v[1], first_obs.v[2],
    );
    
    let obs_positions: Vec<Vector3<f64>> = traj_observed.iter().map(|s| s.r).collect();
    let estimated_x0 = fit_orbit(&init_guess, &obs_positions, dt, steps, 20, 1e-2);
    
    // 4. Set Initial Covariance P0
    let mut p0 = Matrix6::zeros();
    p0[(0, 0)] = 100.0 * 100.0;
    p0[(1, 1)] = 100.0 * 100.0;
    p0[(2, 2)] = 100.0 * 100.0;
    p0[(3, 3)] = 0.1 * 0.1;
    p0[(4, 4)] = 0.1 * 0.1;
    p0[(5, 5)] = 0.1 * 0.1;
    
    // Propagate estimated state with Covariance
    let estimated_state0 = OrbitalState::new(
        Vector3::new(estimated_x0[0], estimated_x0[1], estimated_x0[2]),
        Vector3::new(estimated_x0[3], estimated_x0[4], estimated_x0[5]),
    );
    let (traj_estimated, _estimated_covariances) = propagate_with_covariance_from(&estimated_state0, &p0, dt, steps, 0.0);
    
    // 5. Run Kalman Filter (EKF or UKF)
    let (filter_states, filter_covariances) = if filter_choice == "ukf" {
        println!("Running Unscented Kalman Filter (UKF)...");
        ukf::run_ukf(
            &init_guess,
            &p0,
            &obs_positions,
            dt,
            steps,
            sigma_r,
        )
    } else {
        println!("Running Extended Kalman Filter (EKF)...");
        estimation::run_ekf(
            &init_guess,
            &p0,
            &obs_positions,
            dt,
            steps,
            sigma_r,
        )
    };
    
    let traj_filter: Vec<OrbitalState> = filter_states.iter().map(|x| {
        OrbitalState::new(Vector3::new(x[0], x[1], x[2]), Vector3::new(x[3], x[4], x[5]))
    }).collect();
    
    // 6. Write output CSVs
    write_trajectory_csv(&out_dir.join("truth.csv"), &traj_truth, dt);
    write_trajectory_csv(&out_dir.join("observed.csv"), &traj_observed, dt);
    write_trajectory_csv(&out_dir.join("estimated.csv"), &traj_estimated, dt);
    write_trajectory_csv(&out_dir.join("ekf.csv"), &traj_filter, dt);
    
    write_covariance_csv(&out_dir.join("estimated_covariance.csv"), &filter_covariances, dt);
    
    println!("Truth written: {:?}", out_dir.join("truth.csv"));
    println!("Observed written: {:?}", out_dir.join("observed.csv"));
    println!("Estimated written: {:?}", out_dir.join("estimated.csv"));
    println!("Filter written (ekf.csv): {:?}", out_dir.join("ekf.csv"));
    println!("Covariance written: {:?}", out_dir.join("estimated_covariance.csv"));
    
    // 7. Compute metrics
    let true_x0 = Vector6::new(
        true_state0.r[0], true_state0.r[1], true_state0.r[2],
        true_state0.v[0], true_state0.v[1], true_state0.v[2],
    );
    let initial_pos_err = Vector3::new(
        estimated_x0[0] - true_x0[0],
        estimated_x0[1] - true_x0[1],
        estimated_x0[2] - true_x0[2],
    ).norm();
    
    let initial_vel_err = Vector3::new(
        estimated_x0[3] - true_x0[3],
        estimated_x0[4] - true_x0[4],
        estimated_x0[5] - true_x0[5],
    ).norm();
    
    let mut pos_rmse_sq = 0.0;
    let mut vel_rmse_sq = 0.0;
    for i in 0..steps {
        pos_rmse_sq += (traj_estimated[i].r - traj_truth[i].r).norm_squared();
        vel_rmse_sq += (traj_estimated[i].v - traj_truth[i].v).norm_squared();
    }
    
    let pos_rmse = (pos_rmse_sq / (steps as f64)).sqrt();
    let vel_rmse = (vel_rmse_sq / (steps as f64)).sqrt();
    
    let final_true = &traj_truth[steps - 1];
    let final_filt = filter_states[steps - 1];
    let filter_final_pos_err = Vector3::new(
        final_filt[0] - final_true.r[0],
        final_filt[1] - final_true.r[1],
        final_filt[2] - final_true.r[2],
    ).norm();
    let filter_final_vel_err = Vector3::new(
        final_filt[3] - final_true.v[0],
        final_filt[4] - final_true.v[1],
        final_filt[5] - final_true.v[2],
    ).norm();
    
    let metrics = EstimationMetrics {
        true_initial_state: vec![true_x0[0], true_x0[1], true_x0[2], true_x0[3], true_x0[4], true_x0[5]],
        estimated_initial_state: vec![
            estimated_x0[0], estimated_x0[1], estimated_x0[2],
            estimated_x0[3], estimated_x0[4], estimated_x0[5]
        ],
        initial_position_error_m: initial_pos_err,
        initial_velocity_error_m_s: initial_vel_err,
        trajectory_position_rmse_m: pos_rmse,
        trajectory_velocity_rmse_m_s: vel_rmse,
        ekf_final_position_error_m: filter_final_pos_err,
        ekf_final_velocity_error_m_s: filter_final_vel_err,
    };
    
    let metrics_file = File::create(out_dir.join("estimation_metrics.json")).expect("Failed to create metrics file");
    serde_json::to_writer_pretty(metrics_file, &metrics).expect("Failed to write metrics");
    println!("Estimation metrics written: {:?}", out_dir.join("estimation_metrics.json"));

    // 8. Parallel Conjunction screening using Rayon (integrating propagated covariances)
    let times: Vec<f64> = (1..=steps).map(|idx| idx as f64 * dt).collect();
    let target_positions: Vec<Vector3<f64>> = traj_filter.iter().map(|s| s.r).collect();
    let target_velocities: Vec<Vector3<f64>> = traj_filter.iter().map(|s| s.v).collect();
    let tle_path = Path::new(repo_root).join("data").join("cache").join("active.tle");
    
    let conjunctions = conjunction::run_conjunction_screening(
        &times,
        &target_positions,
        &target_velocities,
        &filter_covariances,
        &tle_path,
        epoch_utc,
        200000.0, // 200 km warning threshold
    );

    let conj_file = File::create(out_dir.join("conjunctions.json")).expect("Failed to create conjunctions file");
    serde_json::to_writer_pretty(conj_file, &conjunctions).expect("Failed to write conjunctions JSON");
    println!("Conjunctions JSON written: {:?}", out_dir.join("conjunctions.json"));

    println!("\n--- TOP 5 CLOSEST APPROACHES & COLLISION RISKS (SCREENED IN PARALLEL) ---");
    println!("{:<10} | {:<24} | {:<20} | {:<10} | {:<12}", "Catalog #", "Name", "Miss Distance (km)", "TCA (sec)", "Pc (Foster)");
    println!("{}", "-".repeat(90));
    for c in conjunctions.iter().take(5) {
        let dist_km = c.min_distance_m / 1000.0;
        println!("{:<10} | {:<24} | {:<20.4} | {:<10.1} | {:<12.3e}", c.sat_id, c.sat_name, dist_km, c.tca_seconds, c.probability_of_collision);
    }
    println!("{}", "-".repeat(90));
}

fn write_trajectory_csv(filepath: &Path, trajectory: &[OrbitalState], dt: f64) {
    let mut wtr = csv::Writer::from_path(filepath).expect("Failed to open CSV file for writing");
    wtr.write_record(&["time", "x", "y", "z", "vx", "vy", "vz"]).expect("Failed to write CSV header");
    
    for (i, s) in trajectory.iter().enumerate() {
        let t = (i + 1) as f64 * dt;
        wtr.write_record(&[
            t.to_string(),
            s.r[0].to_string(),
            s.r[1].to_string(),
            s.r[2].to_string(),
            s.v[0].to_string(),
            s.v[1].to_string(),
            s.v[2].to_string(),
        ]).expect("Failed to write CSV row");
    }
    wtr.flush().expect("Failed to flush CSV writer");
}

fn write_covariance_csv(filepath: &Path, covariances: &[Matrix6<f64>], dt: f64) {
    let mut wtr = csv::Writer::from_path(filepath).expect("Failed to open covariance CSV file for writing");
    wtr.write_record(&["time", "p_xx", "p_xy", "p_xz", "p_yy", "p_yz", "p_zz"]).expect("Failed to write covariance CSV header");
    
    for (i, p) in covariances.iter().enumerate() {
        let t = (i + 1) as f64 * dt;
        wtr.write_record(&[
            t.to_string(),
            p[(0, 0)].to_string(),
            p[(0, 1)].to_string(),
            p[(0, 2)].to_string(),
            p[(1, 1)].to_string(),
            p[(1, 2)].to_string(),
            p[(2, 2)].to_string(),
        ]).expect("Failed to write covariance CSV row");
    }
    wtr.flush().expect("Failed to flush covariance CSV writer");
}

fn propagate_with_maneuver(
    state0: &OrbitalState,
    dt: f64,
    steps: usize,
    maneuver_time: f64,
    dv: &Vector3<f64>,
) -> Vec<OrbitalState> {
    let mut r = state0.r;
    let mut v = state0.v;
    let mut trajectory = Vec::with_capacity(steps);
    
    for i in 0..steps {
        let t = (i as f64) * dt;
        
        // Apply impulsive burn at the closest time step
        if maneuver_time > 0.0 && (t - maneuver_time).abs() < (dt / 2.0) {
            // RTN coordinate axes
            let r_hat = r.normalize();
            let h_hat = r.cross(&v).normalize();
            let t_hat = h_hat.cross(&r_hat).normalize();
            
            let dv_eci = dv[0] * r_hat + dv[1] * t_hat + dv[2] * h_hat;
            v += dv_eci;
            println!("Applying active maneuver at t = {:.1} s: dv_rtn = [{:.3}, {:.3}, {:.3}] m/s, dv_eci = [{:.3}, {:.3}, {:.3}] m/s", t, dv[0], dv[1], dv[2], dv_eci[0], dv_eci[1], dv_eci[2]);
        }
        
        let (r_new, v_new) = rk4_step(|r_curr, v_curr| dynamics::state_derivative(r_curr, v_curr, t), &r, &v, dt);
        r = r_new;
        v = v_new;
        trajectory.push(OrbitalState::new(r, v));
    }
    
    trajectory
}
