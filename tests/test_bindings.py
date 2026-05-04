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
    with pytest.raises(ValueError):
        polygon_area(np.zeros((3, 3)))


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
