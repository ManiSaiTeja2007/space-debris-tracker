module Observe

using ..State
using ..Observation.NoiseModels

export observe_state

function observe_state(
    state::State.OrbitalState,
    σ_r::Float64,
    σ_v::Float64
)
    dr, dv = gaussian_noise(σ_r, σ_v)
    return State.OrbitalState(state.r .+ dr, state.v .+ dv)
end

end
