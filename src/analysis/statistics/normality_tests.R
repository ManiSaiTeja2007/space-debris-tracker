test_normality <- function(errors) {
  list(
    shapiro = shapiro.test(errors),
    ks = ks.test(
      scale(errors),
      "pnorm"
    )
  )
}
