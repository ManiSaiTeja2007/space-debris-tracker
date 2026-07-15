use nalgebra::Vector3;
use crate::constants::{P_SRP, CR, A_OVER_M, R_EARTH};
use crate::third_body::get_sun_position;

/// Computes the Solar Radiation Pressure (SRP) acceleration (m/s^2).
/// Includes a cylindrical shadow model to scale force to zero during eclipses.
pub fn accel_srp(r: &Vector3<f64>, t: f64) -> Vector3<f64> {
    let r_sun = get_sun_position(t);
    let r_sun_target = r - r_sun;
    let d_sun_target = r_sun_target.norm();
    
    if d_sun_target == 0.0 {
        return Vector3::zeros();
    }
    
    let u_sun_target = r_sun_target / d_sun_target;
    
    // 1. Calculate Earth cylindrical shadow factor (nu)
    let u_sun = r_sun.normalize();
    let d_along = r.dot(&u_sun);
    
    let nu = if d_along < 0.0 {
        // Satellite is on the anti-Sun side of Earth
        let r_sq = r.norm_squared();
        let d_perp = (r_sq - d_along * d_along).sqrt();
        if d_perp < R_EARTH {
            0.0 // Full eclipse
        } else {
            1.0 // Fully illuminated
        }
    } else {
        1.0 // Fully illuminated
    };
    
    if nu == 0.0 {
        return Vector3::zeros();
    }
    
    // 2. Compute SRP acceleration
    // a_srp = - P_srp * (A/m) * C_R * nu * u_sun_target
    let accel_mag = P_SRP * A_OVER_M * CR * nu;
    accel_mag * u_sun_target
}
