module Gravity

using LinearAlgebra
using ..Constants

export accel_gravity

function accel_gravity(r::Vector{Float64})
    μ = Constants.μ_EARTH
    norm_r = norm(r)
    return -μ * r / norm_r^3
end

end
