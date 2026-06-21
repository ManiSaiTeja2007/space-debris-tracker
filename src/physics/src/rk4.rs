use nalgebra::Vector3;

pub fn rk4_step<F>(f: F, r: &Vector3<f64>, v: &Vector3<f64>, dt: f64) -> (Vector3<f64>, Vector3<f64>)
where
    F: Fn(&Vector3<f64>, &Vector3<f64>) -> (Vector3<f64>, Vector3<f64>),
{
    let (k1r, k1v) = f(r, v);
    
    let r2 = r + 0.5 * dt * k1r;
    let v2 = v + 0.5 * dt * k1v;
    let (k2r, k2v) = f(&r2, &v2);
    
    let r3 = r + 0.5 * dt * k2r;
    let v3 = v + 0.5 * dt * k2v;
    let (k3r, k3v) = f(&r3, &v3);
    
    let r4 = r + dt * k3r;
    let v4 = v + dt * k3v;
    let (k4r, k4v) = f(&r4, &v4);
    
    let r_new = r + (dt / 6.0) * (k1r + 2.0 * k2r + 2.0 * k3r + k4r);
    let v_new = v + (dt / 6.0) * (k1v + 2.0 * k2v + 2.0 * k3v + k4v);
    
    (r_new, v_new)
}
