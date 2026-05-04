import math

import numpy as np
import pytest

from sparea import AntipodalEdgeError, TooFewVerticesError, polygon_area


# Octant triangle (north pole + two equator points 90° apart).
OCTANT = np.array([
    [0.0,           0.0],            # (1, 0, 0)
    [0.0,           math.pi / 2],    # (0, 1, 0)
    [math.pi / 2,   0.0],            # (0, 0, 1)
])


def test_octant_triangle():
    assert math.isclose(polygon_area(OCTANT), math.pi / 2, abs_tol=1e-13)


def test_two_octant_polygon():
    verts = np.array([
        [0.0,         0.0],            # (1, 0, 0)
        [0.0,         math.pi / 2],    # (0, 1, 0)
        [math.pi / 2, 0.0],            # (0, 0, 1)
        [0.0,        -math.pi / 2],    # (0, -1, 0)
    ])
    assert math.isclose(polygon_area(verts), math.pi, abs_tol=1e-13)


def test_orientation_flip_is_complement():
    # Reversing the traversal yields the area of the complementary
    # region: 4π − interior.
    forward = polygon_area(OCTANT)
    reverse = polygon_area(OCTANT[::-1])
    assert math.isclose(forward + reverse, 4 * math.pi, abs_tol=1e-13)


def test_accepts_python_list():
    verts = [
        (0.0,           0.0),
        (0.0,           math.pi / 2),
        (math.pi / 2,   0.0),
    ]
    assert math.isclose(polygon_area(verts), math.pi / 2, abs_tol=1e-13)


def test_too_few_vertices_raises():
    verts = np.array([[0.0, 0.0], [0.0, math.pi / 2]])
    with pytest.raises(TooFewVerticesError):
        polygon_area(verts)


def test_too_few_vertices_error_is_value_error():
    verts = np.array([[0.0, 0.0]])
    with pytest.raises(ValueError):
        polygon_area(verts)


def test_wrong_shape_raises():
    # (N, 2) and (N, 3) are valid; anything else is not.
    with pytest.raises(ValueError):
        polygon_area(np.zeros((3, 4)))
    with pytest.raises(ValueError):
        polygon_area(np.zeros((3, 1)))


# Octant triangle expressed as unit xyz vectors instead of lat/lng.
OCTANT_XYZ = np.array([
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
])


def test_octant_triangle_xyz():
    assert math.isclose(polygon_area(OCTANT_XYZ), math.pi / 2, abs_tol=1e-14)


def test_xyz_matches_latlng():
    # Same polygon, two input forms — should agree to f64 noise.
    a_latlng = polygon_area(OCTANT)
    a_xyz = polygon_area(OCTANT_XYZ)
    assert math.isclose(a_latlng, a_xyz, abs_tol=1e-14)


def test_xyz_accepts_python_list():
    verts = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    assert math.isclose(polygon_area(verts), math.pi / 2, abs_tol=1e-14)


def test_xyz_too_few_vertices_raises():
    with pytest.raises(TooFewVerticesError):
        polygon_area(np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]))


def test_xyz_antipodal_edge_raises():
    verts = np.array([
        [1.0,  0.0, 0.0],
        [-1.0, 0.0, 0.0],
        [0.0,  0.0, 1.0],
    ])
    with pytest.raises(AntipodalEdgeError):
        polygon_area(verts)


def test_antipodal_edge_raises():
    # (1,0,0) → (-1,0,0) is antipodal; geodesic ambiguous.
    verts = np.array([
        [0.0,         0.0],         # (1, 0, 0)
        [0.0,         math.pi],     # (-1, 0, 0)
        [math.pi / 2, 0.0],         # (0, 0, 1)
    ])
    with pytest.raises(AntipodalEdgeError):
        polygon_area(verts)


def test_antipodal_edge_error_is_value_error():
    verts = np.array([
        [0.0,         0.0],
        [0.0,         math.pi],
        [math.pi / 2, 0.0],
    ])
    with pytest.raises(ValueError):
        polygon_area(verts)
