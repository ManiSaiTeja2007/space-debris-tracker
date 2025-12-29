module State

export OrbitalState

struct OrbitalState
    r::Vector{Float64}   # position (m) [x,y,z]
    v::Vector{Float64}   # velocity (m/s)
end

end
