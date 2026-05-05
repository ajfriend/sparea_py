// Prototype pybind11 binding for sparea.
//
// Compiled by CMake (driven by scikit-build-core) and bundled
// alongside libsparea into the wheel. The Python side imports this
// as `sparea._pb` and exposes `polygon_area` that accepts an `(N, 3)`
// numpy array of unit xyz vectors.

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

namespace py = pybind11;
using namespace py::literals;

// LLVM's optimizer fuses adjacent sin/cos calls on the same argument
// into a sincos() call. That's a glibc extension — MSVC's libm has
// no `sincos`, so when Zig's static archive ends up referencing it on
// Windows, the linker can't resolve it. Provide a one-line shim.
#if defined(_WIN32)
#include <math.h>
extern "C" void sincos(double x, double *s, double *c) {
    *s = sin(x);
    *c = cos(x);
}
#endif

// C ABI exported by libsparea (see src/zig/c_api.zig).
extern "C" {
    int sparea_polygon_area_vec3(const double* verts, std::size_t n, double* out);
}

constexpr int SPAREA_OK = 0;
constexpr int SPAREA_ANTIPODAL_EDGE = 1;
constexpr int SPAREA_TOO_FEW_VERTICES = 2;
constexpr int SPAREA_OOM = 3;

static double polygon_area(
    py::array_t<double, py::array::c_style | py::array::forcecast> verts
) {
    auto buf = verts.unchecked<2>();
    if (buf.shape(1) != 3) {
        throw py::value_error("verts must be a 2-D array of shape (N, 3)");
    }

    double out = 0.0;
    int err = sparea_polygon_area_vec3(buf.data(0, 0), buf.shape(0), &out);

    switch (err) {
        case SPAREA_OK:
            return out;
        case SPAREA_ANTIPODAL_EDGE:
            throw py::value_error(
                "polygon contains an antipodal or near-antipodal edge "
                "(consecutive vertices ~180° apart)"
            );
        case SPAREA_TOO_FEW_VERTICES:
            throw py::value_error(
                "polygon needs at least 3 vertices to bound a region"
            );
        case SPAREA_OOM:
            throw std::bad_alloc();
        default:
            throw py::value_error("sparea: unknown error code");
    }
}

PYBIND11_MODULE(_pb, m) {
    m.doc() = "pybind11 prototype binding for sparea — (N, 3) numpy arrays.";
    m.def("polygon_area", &polygon_area, "verts"_a,
          "Area in steradians of a spherical polygon. `verts` is a "
          "contiguous (N, 3) numpy array of unit xyz vectors.");
}
