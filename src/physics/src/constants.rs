// Earth gravitational parameter (m^3/s^2)
pub const MU_EARTH: f64 = 3.986004418e14;

// Earth mean equatorial radius (meters)
pub const R_EARTH: f64 = 6378137.0;

// Earth J2 coefficient
pub const J2_EARTH: f64 = 1.08262668e-3;

// Earth J3 coefficient
pub const J3_EARTH: f64 = -2.53215306e-6;

// Earth J4 coefficient
pub const J4_EARTH: f64 = -1.61098761e-6;

// Earth rotation rate (rad/s)
pub const OMEGA_EARTH: f64 = 7.2921151467e-5;

// Atmospheric Drag Parameters
pub const CD: f64 = 2.2;              // Drag coefficient
pub const A_OVER_M: f64 = 0.01;        // Area-to-mass ratio (m^2/kg)
// Note: atmosphere density constants moved into drag.rs (5-layer ATMO_TABLE)

// Sun & Moon gravitational parameters (m^3/s^2)
pub const MU_SUN: f64 = 1.32712440018e20;
pub const MU_MOON: f64 = 4.9027779e12;

// Solar Radiation Pressure Constants
pub const P_SRP: f64 = 4.56e-6;        // Solar radiation pressure at 1 AU (N/m^2)
pub const CR: f64 = 1.2;              // Reflectivity coefficient

