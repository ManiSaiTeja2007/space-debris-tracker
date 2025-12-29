load_trajectory <- function(csv_path) {
  df <- read.csv(csv_path)

  list(
    time = df$time,
    r = as.matrix(df[, c("x", "y", "z")]),
    v = as.matrix(df[, c("vx", "vy", "vz")])
  )
}
