module RK4

export rk4_step

function rk4_step(f, r, v, dt)
    k1r, k1v = f(r, v)

    k2r, k2v = f(r .+ 0.5dt*k1r, v .+ 0.5dt*k1v)
    k3r, k3v = f(r .+ 0.5dt*k2r, v .+ 0.5dt*k2v)
    k4r, k4v = f(r .+ dt*k3r, v .+ dt*k3v)

    r_new = r .+ (dt/6)*(k1r + 2k2r + 2k3r + k4r)
    v_new = v .+ (dt/6)*(k1v + 2k2v + 2k3v + k4v)

    return r_new, v_new
end

end
