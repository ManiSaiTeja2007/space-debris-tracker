# ============================================================
# compute_metrics.R (R Statistics & Performance Evaluation)
# ============================================================

compute_metrics <- function(residuals) {
  # residuals is a list from compute_residuals containing:
  # pos_error, vel_error
  
  pos_rmse <- sqrt(mean(residuals$pos_error^2))
  vel_rmse <- sqrt(mean(residuals$vel_error^2))
  
  pos_mean <- mean(residuals$pos_error)
  vel_mean <- mean(residuals$vel_error)
  
  pos_max  <- max(residuals$pos_error)
  vel_max  <- max(residuals$vel_error)
  
  pos_sd   <- sd(residuals$pos_error)
  vel_sd   <- sd(residuals$vel_error)
  
  list(
    rmse_pos_m = pos_rmse,
    rmse_vel_m_s = vel_rmse,
    mean_pos_m = pos_mean,
    mean_vel_m_s = vel_mean,
    max_pos_m = pos_max,
    max_vel_m_s = vel_max,
    sd_pos_m = pos_sd,
    sd_vel_m_s = vel_sd
  )
}
