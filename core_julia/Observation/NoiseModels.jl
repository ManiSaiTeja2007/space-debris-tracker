module NoiseModels

using Random, LinearAlgebra

export gaussian_noise

"""
Gaussian noise for position & velocity
σ_r : position std (m)
σ_v : velocity std (m/s)
"""
function gaussian_noise(σ_r::Float64, σ_v::Float64)
    dr = σ_r .* randn(3)
    dv = σ_v .* randn(3)
    return dr, dv
end

end
