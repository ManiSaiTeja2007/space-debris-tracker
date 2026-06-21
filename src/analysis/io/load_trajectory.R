# ============================================================
# load_trajectory.R (R Trajectory Loader)
# ============================================================

load_trajectory <- function(path) {
  if (!file.exists(path)) {
    stop(paste("Trajectory file not found:", path))
  }
  
  df <- read.csv(path)
  
  list(
    time = df$time,
    r = as.matrix(df[, c("x", "y", "z")]),
    v = as.matrix(df[, c("vx", "vy", "vz")])
  )
}
