module Propagator

using ..State
using ..Dynamics
using ..RK4

export propagate

function propagate(state::State.OrbitalState, dt::Float64, steps::Int)
    r = copy(state.r)
    v = copy(state.v)

    trajectory = Vector{State.OrbitalState}()

    for _ in 1:steps
        r, v = RK4.rk4_step(Dynamics.state_derivative, r, v, dt)
        push!(trajectory, State.OrbitalState(r, v))
    end

    return trajectory
end

end
