# ============================================================
# main.R (R Orchestration Script)
# ============================================================

source("io/load_trajectory.R")
source("residuals/compute_residuals.R")
source("statistics/compute_metrics.R")

truth_path <- "../../data/generated/truth.csv"
obs_path   <- "../../data/generated/observed.csv"
est_path   <- "../../data/generated/estimated.csv"
output_json <- "../../data/generated/statistics.json"

cat("\n============================================================\n")
cat(">> RUNNING: R Statistical Analysis & Residuals\n")
cat("============================================================\n")

if (!file.exists(truth_path)) {
  stop(paste("Truth trajectory not found at:", truth_path))
}

truth <- load_trajectory(truth_path)

# 1. Analyze Observation Errors (if observed.csv exists)
obs_metrics <- list()
if (file.exists(obs_path)) {
  cat("Analyzing Observation Residuals (Noisy observations vs Truth)...\n")
  obs <- load_trajectory(obs_path)
  obs_res <- compute_residuals(truth, obs)
  obs_metrics <- compute_metrics(obs_res)
  
  cat("Observation Position Error (m):\n")
  cat(paste("  RMSE: ", round(obs_metrics$rmse_pos_m, 2), " m\n"))
  cat(paste("  Max:  ", round(obs_metrics$max_pos_m, 2), " m\n"))
}

# 2. Analyze Tracking/Estimation Errors (if estimated.csv exists)
est_metrics <- list()
if (file.exists(est_path)) {
  cat("\nAnalyzing Tracking Residuals (Estimated trajectory vs Truth)...\n")
  est <- load_trajectory(est_path)
  est_res <- compute_residuals(truth, est)
  est_metrics <- compute_metrics(est_res)
  
  cat("Estimated Trajectory Position Error (m):\n")
  cat(paste("  RMSE: ", round(est_metrics$rmse_pos_m, 2), " m\n"))
  cat(paste("  Max:  ", round(est_metrics$max_pos_m, 2), " m\n"))
}

# 3. Write Metrics to JSON (Manual format to avoid JSON dependency issues in basic R installations)
write_json <- function(obs_m, est_m, file_path) {
  json_str <- "{\n"
  
  # Format observation metrics
  if (length(obs_m) > 0) {
    json_str <- paste0(json_str, "  \"observation_error\": {\n")
    json_str <- paste0(json_str, "    \"rmse_pos_m\": ", obs_m$rmse_pos_m, ",\n")
    json_str <- paste0(json_str, "    \"rmse_vel_m_s\": ", obs_m$rmse_vel_m_s, ",\n")
    json_str <- paste0(json_str, "    \"mean_pos_m\": ", obs_m$mean_pos_m, ",\n")
    json_str <- paste0(json_str, "    \"max_pos_m\": ", obs_m$max_pos_m, ",\n")
    json_str <- paste0(json_str, "    \"sd_pos_m\": ", obs_m$sd_pos_m, "\n")
    json_str <- paste0(json_str, "  }")
  }
  
  # Format estimation metrics
  if (length(est_m) > 0) {
    if (length(obs_m) > 0) {
      json_str <- paste0(json_str, ",\n")
    }
    json_str <- paste0(json_str, "  \"tracking_error\": {\n")
    json_str <- paste0(json_str, "    \"rmse_pos_m\": ", est_m$rmse_pos_m, ",\n")
    json_str <- paste0(json_str, "    \"rmse_vel_m_s\": ", est_m$rmse_vel_m_s, ",\n")
    json_str <- paste0(json_str, "    \"mean_pos_m\": ", est_m$mean_pos_m, ",\n")
    json_str <- paste0(json_str, "    \"max_pos_m\": ", est_m$max_pos_m, ",\n")
    json_str <- paste0(json_str, "    \"sd_pos_m\": ", est_m$sd_pos_m, "\n")
    json_str <- paste0(json_str, "  }")
  }
  
  json_str <- paste0(json_str, "\n}\n")
  writeLines(json_str, file_path)
}

write_json(obs_metrics, est_metrics, output_json)
cat(paste("\nSaved statistical report to:", output_json, "\n"))
cat("[SUCCESS] COMPLETED: R Statistical Analysis & Residuals\n")
