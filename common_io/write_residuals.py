def write_residuals(path, times, residuals, definition):
    """
    definition: string describing EXACT meaning of residual
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(f"# residual_definition: {definition}\n")
        f.write("time,residual_m\n")
        for t, r in zip(times, residuals):
            f.write(f"{t},{r}\n")
