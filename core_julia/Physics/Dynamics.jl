module Dynamics

using ..Gravity
using ..J2

export state_derivative

function state_derivative(r::Vector{Float64}, v::Vector{Float64})
    a = Gravity.accel_gravity(r) + J2.accel_J2(r)
    return v, a
end

end
