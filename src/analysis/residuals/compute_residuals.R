compute_residuals <- function(truth, obs) {
  stopifnot(length(truth$time) == length(obs$time))

  dr <- obs$r - truth$r
  dv <- obs$v - truth$v

  list(
    time = truth$time,
    pos_error = sqrt(rowSums(dr^2)),
    vel_error = sqrt(rowSums(dv^2))
  )
}
