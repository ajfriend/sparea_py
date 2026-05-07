import math

import numpy as np
import pytest

import sparea as sp


# Octant triangle (north pole + two equator points 90° apart).
OCTANT_DEG = np.array([
    [0.0,  0.0],   # (1, 0, 0)
    [0.0, 90.0],   # (0, 1, 0)
    [90.0, 0.0],   # (0, 0, 1)
])

OCTANT_RAD = np.radians(OCTANT_DEG)

OCTANT_XYZ = np.array([
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
])

# Hemisphere polygon — vertices straddle the equator so the centroid
# fan is not well-conditioned, forcing auto-dispatch onto the angle
# kernel. Area = π (half the sphere).
HALF_SPHERE_DEG = np.array([
    [0.0,   0.0],   # (1,  0, 0)
    [0.0,  90.0],   # (0,  1, 0)
    [90.0,  0.0],   # (0,  0, 1)
    [0.0, -90.0],   # (0, -1, 0)
])


@pytest.mark.parametrize('verts,geo', [
    (OCTANT_DEG, 'latlng'),       # default = degrees
    (OCTANT_DEG, 'latlng_deg'),   # explicit degrees
    (OCTANT_RAD, 'latlng_rad'),   # explicit radians
    (OCTANT_XYZ, 'vec3'),
])
@pytest.mark.parametrize('algo', ['auto', 'cross', 'angle'])
def test_octant_area(verts, geo, algo):
    assert math.isclose(
        sp.area(verts, geo=geo, algo=algo), math.pi / 2, abs_tol=1e-13
    )


def test_xyz_matches_latlng():
    a_latlng = sp.area(OCTANT_DEG)
    a_xyz = sp.area(OCTANT_XYZ, geo='vec3')
    assert math.isclose(a_latlng, a_xyz, abs_tol=1e-13)


def test_half_sphere_auto_routes_to_angle():
    # Not hemisphere-contained — `auto` falls back to the angle kernel.
    assert math.isclose(sp.area(HALF_SPHERE_DEG), math.pi, abs_tol=1e-13)


def test_orientation_flip_is_complement():
    fwd = sp.area(OCTANT_DEG)
    rev = sp.area(OCTANT_DEG[::-1])
    assert math.isclose(fwd + rev, 4 * math.pi, abs_tol=1e-13)


def test_accepts_python_list_latlng():
    verts = [
        (0.0,  0.0),
        (0.0, 90.0),
        (90.0, 0.0),
    ]
    assert math.isclose(sp.area(verts), math.pi / 2, abs_tol=1e-13)


def test_accepts_python_list_vec3():
    verts = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    assert math.isclose(
        sp.area(verts, geo='vec3'), math.pi / 2, abs_tol=1e-14
    )


def test_invalid_geo():
    with pytest.raises(ValueError, match='geo must be'):
        sp.area(OCTANT_DEG, geo='xyz')


def test_invalid_algo():
    with pytest.raises(ValueError, match='algo must be'):
        sp.area(OCTANT_DEG, algo='bogus')


@pytest.mark.parametrize('verts,geo,cols', [
    (OCTANT_XYZ, 'latlng', 2),  # 3 cols passed for geo='latlng'
    (OCTANT_DEG, 'vec3',   3),  # 2 cols passed for geo='vec3'
])
def test_shape_mismatch(verts, geo, cols):
    with pytest.raises(ValueError, match=rf'\(N, {cols}\)'):
        sp.area(verts, geo=geo)


def test_shape_not_2d():
    with pytest.raises(ValueError):
        sp.area(np.zeros(6))


@pytest.mark.parametrize('verts,geo', [
    (np.array([[0.0, 0.0], [0.0, 90.0]]), 'latlng'),
    (np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]), 'vec3'),
])
def test_too_few_vertices(verts, geo):
    with pytest.raises(ValueError, match='at least 3'):
        sp.area(verts, geo=geo)


@pytest.mark.parametrize('verts,geo', [
    (np.array([[0.0, 0.0], [0.0, 180.0], [90.0, 0.0]]), 'latlng'),
    (np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]), 'vec3'),
])
def test_antipodal_edge(verts, geo):
    with pytest.raises(ValueError, match='antipodal'):
        sp.area(verts, geo=geo)


def test_signed_returns_negative_for_reversed_orientation():
    # CCW from outside the sphere ⇒ +π/2; reversing the traversal
    # ⇒ −π/2. Default `signed=False` would fold the negative into
    # 4π − π/2; `signed=True` keeps it raw.
    fwd = sp.area(OCTANT_DEG, signed=True)
    rev = sp.area(OCTANT_DEG[::-1], signed=True)
    assert math.isclose(fwd, math.pi / 2, abs_tol=1e-13)
    assert math.isclose(rev, -math.pi / 2, abs_tol=1e-13)
    assert math.isclose(fwd + rev, 0.0, abs_tol=1e-13)
