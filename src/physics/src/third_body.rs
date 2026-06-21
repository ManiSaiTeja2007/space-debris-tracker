use nalgebra::Vector3;
use std::f64::consts::PI;
use crate::constants::{MU_SUN, MU_MOON};

/// Approximates the position of the Sun relative to the Earth (in ECI meters).
pub fn get_sun_position(t: f64) -> Vector3<f64> {
    // Days since J2000 (roughly Jan 1, 2024 at 00:00 is JD 2460310.5)
    // J2000 is JD 2451545.0. Difference is 8765.5 days.
    let days = 8765.5 + t / 86400.0;
    
    // Mean longitude of the Sun
    let l = (280.460 + 0.9856474 * days).rem_euclid(360.0) * PI / 180.0;
    // Mean anomaly of the Sun
    let g = (357.528 + 0.9856003 * days).rem_euclid(360.0) * PI / 180.0;
    // Ecliptic longitude
    let lambda = l + (1.915 * g.sin() + 0.020 * (2.0 * g).sin()) * PI / 180.0;
    
    let obliq = 23.439 * PI / 180.0;
    let d_sun = 1.495978707e11; // 1 AU in meters
    
    Vector3::new(
        d_sun * lambda.cos(),
        d_sun * lambda.sin() * obliq.cos(),
        d_sun * lambda.sin() * obliq.sin()
    )
}

/// Approximates the position of the Moon relative to the Earth (in ECI meters).
pub fn get_moon_position(t: f64) -> Vector3<f64> {
    let days = 8765.5 + t / 86400.0;
    
    // Moon's mean longitude
    let lambda_m = (218.316 + 13.176396 * days).rem_euclid(360.0) * PI / 180.0;
    // Moon's mean anomaly
    let m_m = (134.963 + 13.064993 * days).rem_euclid(360.0) * PI / 180.0;
    // Moon's mean latitude parameter
    let f_m = (93.272 + 13.229350 * days).rem_euclid(360.0) * PI / 180.0;
    
    // Ecliptic longitude and latitude
    let lambda = lambda_m + 6.289 * m_m.sin() * PI / 180.0;
    let beta = 5.128 * f_m.sin() * PI / 180.0;
    
    let obliq = 23.439 * PI / 180.0;
    let d_moon = 3.844e8; // meters
    
    // Convert ecliptic to ECI (inertial) coordinates
    let x_ecl = d_moon * lambda.cos() * beta.cos();
    let y_ecl = d_moon * lambda.sin() * beta.cos();
    let z_ecl = d_moon * beta.sin();
    
    Vector3::new(
        x_ecl,
        y_ecl * obliq.cos() - z_ecl * obliq.sin(),
        y_ecl * obliq.sin() + z_ecl * obliq.cos()
    )
}

/// Computes the third-body perturbation acceleration vector (m/s^2).
pub fn accel_third_body(r: &Vector3<f64>, r_body: &Vector3<f64>, mu_body: f64) -> Vector3<f64> {
    let r_diff = r_body - r;
    let d_diff = r_diff.norm();
    let d_body = r_body.norm();
    
    mu_body * (r_diff / (d_diff * d_diff * d_diff) - r_body / (d_body * d_body * d_body))
}

/// Combined third-body perturbation from Sun and Moon.
pub fn third_body_perturbation(r: &Vector3<f64>, t: f64) -> Vector3<f64> {
    let r_sun = get_sun_position(t);
    let r_moon = get_moon_position(t);
    
    accel_third_body(r, &r_sun, MU_SUN) + accel_third_body(r, &r_moon, MU_MOON)
}
