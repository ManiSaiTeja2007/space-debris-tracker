source("io/load_trajectory.R")
source("residuals/compute_residuals.R")

truth_path <- "../data/generated/truth.csv"
obs_path   <- "../data/generated/observed.csv"

if (!file.exists(obs_path)) {
  cat("No observed.csv found. Skipping residual analysis.\n")
  quit(save="no")
}

truth <- load_trajectory(truth_path)
obs   <- load_trajectory(obs_path)

res <- compute_residuals(truth, obs)

cat("Position error summary:\n")
print(summary(res$pos_error))

hist(
  res$pos_error,
  breaks = 50,
  main = "Position Error Distribution",
  xlab = "Error (m)"
)
