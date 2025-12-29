module J2

using LinearAlgebra
using ..Constants

export accel_J2

function accel_J2(r::Vector{Float64})
    μ = Constants.μ_EARTH
    R = Constants.R_EARTH
    J2 = Constants.J2_EARTH

    x, y, z = r
    r_norm = norm(r)
    r2 = r_norm^2
    z2 = z^2

    factor = (3/2) * J2 * μ * R^2 / r_norm^5

    ax = factor * x * (5*z2/r2 - 1)
    ay = factor * y * (5*z2/r2 - 1)
    az = factor * z * (5*z2/r2 - 3)

    return [ax, ay, az]
end

end
