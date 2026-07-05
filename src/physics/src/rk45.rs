use nalgebra::Vector3;

/// Dormand-Prince RK45 single step.
/// Returns (r_new, v_new, error_norm, h_suggested_next)
pub fn rk45_step<F>(
    f: &F,
    r: &Vector3<f64>,
    v: &Vector3<f64>,
    t: f64,
    h: f64,
    atol: f64,
    rtol: f64,
) -> (Vector3<f64>, Vector3<f64>, f64, f64)
where
    F: Fn(&Vector3<f64>, &Vector3<f64>, f64) -> (Vector3<f64>, Vector3<f64>),
{
    // Dormand-Prince tableau coefficients
    let c2 = 1.0/5.0; let c3 = 3.0/10.0; let c4 = 4.0/5.0; let c5 = 8.0/9.0;
    let a21 = 1.0/5.0;
    let a31 = 3.0/40.0;  let a32 = 9.0/40.0;
    let a41 = 44.0/45.0; let a42 = -56.0/15.0;  let a43 = 32.0/9.0;
    let a51 = 19372.0/6561.0; let a52 = -25360.0/2187.0; let a53 = 64448.0/6561.0; let a54 = -212.0/729.0;
    let a61 = 9017.0/3168.0; let a62 = -355.0/33.0; let a63 = 46732.0/5247.0; let a64 = 49.0/176.0; let a65 = -5103.0/18656.0;

    // 5th order weights
    let b1 = 35.0/384.0; let b3 = 500.0/1113.0; let b4 = 125.0/192.0; let b5 = -2187.0/6784.0; let b6 = 11.0/84.0;
    // Error = 5th - 4th order
    let e1 = 71.0/57600.0; let e3 = -71.0/16695.0; let e4 = 71.0/1920.0; let e5 = -17253.0/339200.0; let e6 = 22.0/525.0; let e7 = -1.0/40.0;

    let (k1r, k1v) = f(r, v, t);
    let r2 = r + h * a21 * k1r;
    let v2 = v + h * a21 * k1v;
    let (k2r, k2v) = f(&r2, &v2, t + c2*h);
    let r3 = r + h * (a31*k1r + a32*k2r);
    let v3 = v + h * (a31*k1v + a32*k2v);
    let (k3r, k3v) = f(&r3, &v3, t + c3*h);
    let r4 = r + h * (a41*k1r + a42*k2r + a43*k3r);
    let v4 = v + h * (a41*k1v + a42*k2v + a43*k3v);
    let (k4r, k4v) = f(&r4, &v4, t + c4*h);
    let r5 = r + h * (a51*k1r + a52*k2r + a53*k3r + a54*k4r);
    let v5 = v + h * (a51*k1v + a52*k2v + a53*k3v + a54*k4v);
    let (k5r, k5v) = f(&r5, &v5, t + c5*h);
    let r6 = r + h * (a61*k1r + a62*k2r + a63*k3r + a64*k4r + a65*k5r);
    let v6 = v + h * (a61*k1v + a62*k2v + a63*k3v + a64*k4v + a65*k5v);
    let (k6r, k6v) = f(&r6, &v6, t + h);

    // 5th order solution
    let r_new = r + h * (b1*k1r + b3*k3r + b4*k4r + b5*k5r + b6*k6r);
    let v_new = v + h * (b1*k1v + b3*k3v + b4*k4v + b5*k5v + b6*k6v);

    // Error estimate (need k7)
    let (k7r, k7v) = f(&r_new, &v_new, t + h);
    let err_r = h * (e1*k1r + e3*k3r + e4*k4r + e5*k5r + e6*k6r + e7*k7r);
    let err_v = h * (e1*k1v + e3*k3v + e4*k4v + e5*k5v + e6*k6v + e7*k7v);

    // Error norm (mixed position/velocity scaled)
    let sc_r = atol + rtol * r.norm().max(r_new.norm());
    let sc_v = atol + rtol * v.norm().max(v_new.norm());
    let err_norm = ((err_r.norm_squared() / (sc_r * sc_r) + err_v.norm_squared() / (sc_v * sc_v)) / 6.0).sqrt();

    // Step size suggestion
    let h_new = if err_norm > 0.0 {
        h * (0.9 * err_norm.powf(-0.2)).clamp(0.1, 5.0)
    } else {
        h * 5.0
    };

    (r_new, v_new, err_norm, h_new)
}

/// Adaptive propagation using RK45 for a fixed number of output points.
/// Internally sub-steps as needed to meet tolerance, outputs at uniform dt intervals.
pub fn propagate_rk45<F>(
    f: &F,
    r0: &Vector3<f64>,
    v0: &Vector3<f64>,
    t_start: f64,
    dt: f64,
    steps: usize,
    atol: f64,
    rtol: f64,
) -> Vec<(Vector3<f64>, Vector3<f64>)>
where
    F: Fn(&Vector3<f64>, &Vector3<f64>, f64) -> (Vector3<f64>, Vector3<f64>),
{
    let mut results = Vec::with_capacity(steps);
    let mut r = *r0;
    let mut v = *v0;
    let h_min = 0.01_f64;
    let h_max = dt;

    for step in 0..steps {
        let t0 = t_start + (step as f64) * dt;
        let t1 = t0 + dt;
        let mut t_curr = t0;
        let mut h = dt.min(h_max);

        while t_curr < t1 - 1e-10 {
            let h_try = h.min(t1 - t_curr);
            let (r_new, v_new, err_norm, h_next) = rk45_step(f, &r, &v, t_curr, h_try, atol, rtol);
            if err_norm <= 1.0 || h_try <= h_min {
                r = r_new;
                v = v_new;
                t_curr += h_try;
            }
            h = h_next.clamp(h_min, h_max);
        }
        results.push((r, v));
    }
    results
}
