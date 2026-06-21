fit_error_distribution <- function(errors) {
  list(
    mean = mean(errors),
    sd = sd(errors),
    median = median(errors),
    iqr = IQR(errors)
  )
}
