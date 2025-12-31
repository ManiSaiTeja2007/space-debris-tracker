# ============================================================
# Circular Orbit Test (v0.1 + v0.2 compatible)
# ============================================================

include("../Core/Constants.jl")
include("../Core/State.jl")
include("../Physics/Gravity.jl")
include("../Physics/J2.jl")
include("../Physics/Dynamics.jl")
include("../Propagation/RK4.jl")
include("../Propagation/Propagator.jl")

using .Constants
using .State
using .Propagator
using LinearAlgebra
using Random

# ------------------------------------------------------------
# Read command-line arguments (ROBUST)
# ------------------------------------------------------------
if length(ARGS) < 1
    error("REPO_ROOT argument not provided")
end

repo_root = ARGS[1]

ENABLE_NOISE = length(ARGS) >= 2 && ARGS[2] == "1"
σ_r = length(ARGS) >= 3 ? parse(Float64, ARGS[3]) : 0.0
σ_v = length(ARGS) >= 4 ? parse(Float64, ARGS[4]) : 0.0
out_dir = joinpath(repo_root, "data", "generated")
mkpath(out_dir)

# ------------------------------------------------------------
# Parameters (v0.2 controlled, v0.1 default-safe)
# ------------------------------------------------------------

Random.seed!(42)

# ------------------------------------------------------------
# Initial Orbit (unchanged)
# ------------------------------------------------------------
altitude = 400e3
r0_mag = Constants.R_EARTH + altitude
v0_mag = sqrt(Constants.μ_EARTH / r0_mag)

state0 = State.OrbitalState(
    [r0_mag, 0.0, 0.0],
    [0.0, v0_mag, 0.0]
)

dt = 10.0
steps = Int(5400 / dt)

traj = Propagator.propagate(state0, dt, steps)

# ------------------------------------------------------------
# Helper: noise injection (ONLY if enabled)
# ------------------------------------------------------------
function noisy_state(s::State.OrbitalState)
    if !ENABLE_NOISE
        return s
    end
    dr = σ_r .* randn(3)
    dv = σ_v .* randn(3)
    return State.OrbitalState(s.r .+ dr, s.v .+ dv)
end

# ------------------------------------------------------------
# Write TRUTH
# ------------------------------------------------------------
truth_path = joinpath(out_dir, "truth.csv")
open(truth_path, "w") do io
    write(io, "time,x,y,z,vx,vy,vz\n")
    for (i, s) in enumerate(traj)
        write(io,
            "$(i*dt),$(s.r[1]),$(s.r[2]),$(s.r[3]),$(s.v[1]),$(s.v[2]),$(s.v[3])\n"
        )
    end
end

println("Truth written: ", truth_path)

# ------------------------------------------------------------
# Write OBSERVED (only if noise enabled)
# ------------------------------------------------------------
if ENABLE_NOISE
    obs_path = joinpath(out_dir, "observed.csv")
    open(obs_path, "w") do io
        write(io, "time,x,y,z,vx,vy,vz\n")
        for (i, s) in enumerate(traj)
            o = noisy_state(s)
            write(io,
                "$(i*dt),$(o.r[1]),$(o.r[2]),$(o.r[3]),$(o.v[1]),$(o.v[2]),$(o.v[3])\n"
            )
        end
    end
    println("Observed written: ", obs_path)
end
