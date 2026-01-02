from coords.eci_ecef import eci_to_ecef


def test_equator_point():
    # Known point on equator at GMST = 0
    r_eci = [6378137, 0, 0]
    r_ecef = eci_to_ecef(r_eci, known_time)
    assert abs(r_ecef[0] - 6378137) < 1e-3
