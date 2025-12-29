plot_error_growth <- function(residuals) {
  plot(
    residuals$time,
    residuals$pos_error,
    type = "l",
    col = "red",
    xlab = "Time (s)",
    ylab = "Position Error (m)",
    main = "Position Error Growth"
  )
}
