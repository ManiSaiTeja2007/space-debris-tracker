use std::fs;
use std::path::Path;
use nalgebra::{Vector3, Vector2, Matrix3, Matrix2, Matrix6};
use serde::Serialize;
use rayon::prelude::*;
use chrono::{DateTime, Utc};
use sgp4::{Elements, Constants, MinutesSinceEpoch};

#[derive(Serialize, Clone)]
pub struct Conjunction {
    pub sat_name: String,
    pub sat_id: u64,
    pub min_distance_m: f64,
    pub tca_seconds: f64,
    pub tca_utc: String,
    pub relative_position_m: Vec<f64>,
    pub relative_velocity_m_s: Vec<f64>,
    pub sat_position_m: Vec<f64>,
    pub sat_velocity_m_s: Vec<f64>,
    pub probability_of_collision: f64,
}

pub fn run_conjunction_screening(
    times: &[f64],
    target_positions: &[Vector3<f64>],
    target_velocities: &[Vector3<f64>],
    target_covariances: &[Matrix6<f64>],
    tle_path: &Path,
    epoch_utc: DateTime<Utc>,
    warning_threshold: f64,
) -> Vec<Conjunction> {
    if !tle_path.exists() {
        println!("[WARNING] TLE catalog not found at {:?}. Skipping conjunction analysis.", tle_path);
        return Vec::new();
    }

    let content = match fs::read_to_string(tle_path) {
        Ok(c) => c,
        Err(e) => {
            println!("[WARNING] Could not read TLE file: {e}. Skipping conjunction analysis.");
            return Vec::new();
        }
    };

    // Parse TLE groups
    let lines: Vec<&str> = content.lines().collect();
    let mut tle_entries = Vec::new();
    
    let mut i = 0;
    while i < lines.len() {
        let name_line = lines[i].trim();
        if name_line.is_empty() {
            i += 1;
            continue;
        }
        
        let mut line1 = "";
        let mut line2 = "";
        
        let mut j = i + 1;
        while j < lines.len() && line1.is_empty() {
            let l = lines[j].trim();
            if !l.is_empty() {
                line1 = l;
            }
            j += 1;
        }
        
        while j < lines.len() && line2.is_empty() {
            let l = lines[j].trim();
            if !l.is_empty() {
                line2 = l;
            }
            j += 1;
        }
        
        if !line1.is_empty() && !line2.is_empty() && line1.starts_with('1') && line2.starts_with('2') {
            tle_entries.push((name_line.to_string(), line1.to_string(), line2.to_string()));
            i = j;
        } else {
            i += 1;
        }
    }

    println!("Conjunctions: Screening {} satellites in parallel...", tle_entries.len());
    let steps = times.len();
    let collision_radius = 20.0; // 20 meters combined target + debris radius

    let mut results: Vec<Conjunction> = tle_entries
        .par_iter()
        .filter_map(|(name, l1, l2)| {
            let elements = match Elements::from_tle(Some(name.clone()), l1.as_bytes(), l2.as_bytes()) {
                Ok(el) => el,
                Err(_) => return None,
            };

            let constants = match Constants::from_elements(&elements) {
                Ok(c) => c,
                Err(_) => return None,
            };

            let mut min_dist = f64::INFINITY;
            let mut tca_sec = 0.0;
            let mut tca_idx = 0;
            let mut sat_pos_tca = Vector3::zeros();
            let mut sat_vel_tca = Vector3::zeros();
            let mut r_rel_tca = Vector3::zeros();
            let mut v_rel_tca = Vector3::zeros();

            for idx in 0..steps {
                let t = times[idx];
                let step_time = epoch_utc + chrono::Duration::milliseconds((t * 1000.0) as i64);
                let diff = step_time.naive_utc() - elements.datetime;
                let mins = diff.num_milliseconds() as f64 / 60000.0;

                let time_param = MinutesSinceEpoch(mins);
                let prediction = match constants.propagate(time_param) {
                    Ok(p) => p,
                    Err(_) => continue,
                };

                let r_m = Vector3::new(prediction.position[0], prediction.position[1], prediction.position[2]) * 1000.0;
                let v_m = Vector3::new(prediction.velocity[0], prediction.velocity[1], prediction.velocity[2]) * 1000.0;

                let dist = (target_positions[idx] - r_m).norm();
                if dist < min_dist {
                    min_dist = dist;
                    tca_sec = t;
                    tca_idx = idx;
                    sat_pos_tca = r_m;
                    sat_vel_tca = v_m;
                    r_rel_tca = r_m - target_positions[idx];
                    v_rel_tca = v_m - target_velocities[idx];
                }
            }

            if min_dist <= warning_threshold {
                let tca_utc = epoch_utc + chrono::Duration::milliseconds((tca_sec * 1000.0) as i64);
                
                // Calculate Foster's 2D Probability of Collision (Pc) at TCA
                let p_target = target_covariances[tca_idx].fixed_view::<3, 3>(0, 0);
                
                // Debris position covariance: assumed 100m standard deviation
                let p_debris = Matrix3::from_diagonal(&Vector3::repeat(100.0 * 100.0));
                let p_combined = p_target + p_debris;
                
                // Relative velocity at TCA
                let relative_vel = v_rel_tca;
                let relative_vel_norm = relative_vel.normalize();
                
                // Construct B-plane (encounter plane) coordinate system
                let mut x_axis = target_positions[tca_idx].cross(&relative_vel_norm);
                if x_axis.norm() < 1e-6 {
                    x_axis = Vector3::new(1.0, 0.0, 0.0).cross(&relative_vel_norm);
                    if x_axis.norm() < 1e-6 {
                        x_axis = Vector3::new(0.0, 1.0, 0.0).cross(&relative_vel_norm);
                    }
                }
                let x_axis = x_axis.normalize();
                let y_axis = relative_vel_norm.cross(&x_axis).normalize();
                
                // Transformation matrix from ECI to encounter frame
                let r_enc = Matrix3::from_rows(&[
                    x_axis.transpose(),
                    y_axis.transpose(),
                    relative_vel_norm.transpose()
                ]);
                
                // Project covariance and relative position onto encounter plane
                let p_proj = &r_enc * &p_combined * r_enc.transpose();
                let r_proj = &r_enc * r_rel_tca;
                
                // 2D parts in the B-plane (X and Y only)
                let p_2d = Matrix2::new(
                    p_proj[(0, 0)], p_proj[(0, 1)],
                    p_proj[(1, 0)], p_proj[(1, 1)]
                );
                let r_2d = Vector2::new(r_proj[0], r_proj[1]);
                
                // Foster's Pc computation
                let det = p_2d.determinant();
                let mut probability_of_collision = 0.0;
                
                if det > 1e-12 {
                    if let Some(p_2d_inv) = p_2d.try_inverse() {
                        let exponent = -0.5 * (r_2d.transpose() * p_2d_inv * r_2d)[0];
                        probability_of_collision = (collision_radius * collision_radius) / (2.0 * det.sqrt()) * exponent.exp();
                    }
                }
                
                // Cap probability to 1.0 in case of numerical bounds
                if probability_of_collision > 1.0 {
                    probability_of_collision = 1.0;
                }

                Some(Conjunction {
                    sat_name: name.clone(),
                    sat_id: elements.norad_id,
                    min_distance_m: min_dist,
                    tca_seconds: tca_sec,
                    tca_utc: tca_utc.to_rfc3339(),
                    relative_position_m: vec![r_rel_tca[0], r_rel_tca[1], r_rel_tca[2]],
                    relative_velocity_m_s: vec![v_rel_tca[0], v_rel_tca[1], v_rel_tca[2]],
                    sat_position_m: vec![sat_pos_tca[0], sat_pos_tca[1], sat_pos_tca[2]],
                    sat_velocity_m_s: vec![sat_vel_tca[0], sat_vel_tca[1], sat_vel_tca[2]],
                    probability_of_collision,
                })
            } else {
                None
            }
        })
        .collect();

    // Sort by collision probability descending (highest risk first)
    results.sort_by(|a, b| b.probability_of_collision.partial_cmp(&a.probability_of_collision).unwrap_or(std::cmp::Ordering::Equal));
    results
}
