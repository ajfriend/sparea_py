// Prototype nanobind binding for sparea.
//
// Compiled by CMake (driven by scikit-build-core) and statically
// linked against libsparea. The Python side imports this as
// `sparea._nb` and exposes `polygon_area` that accepts `(N, 3)` numpy
// arrays with zero copy.

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>

namespace nb = nanobind;
using namespace nb::literals;

// C ABI exported by libsparea (see src/zig/c_api.zig).
extern "C" {
    int sparea_polygon_area_vec3(const double* verts, std::size_t n, double* out);
}

constexpr int SPAREA_OK = 0;
constexpr int SPAREA_ANTIPODAL_EDGE = 1;
constexpr int SPAREA_TOO_FEW_VERTICES = 2;
constexpr int SPAREA_OOM = 3;

static double polygon_area(
    nb::ndarray<const double, nb::shape<-1, 3>, nb::c_contig, nb::device::cpu> verts
) {
    double out = 0.0;
    int err = sparea_polygon_area_vec3(verts.data(), verts.shape(0), &out);

    switch (err) {
        case SPAREA_OK:
            return out;
        case SPAREA_ANTIPODAL_EDGE:
            throw nb::value_error(
                "polygon contains an antipodal or near-antipodal edge "
                "(consecutive vertices ~180° apart)"
            );
        case SPAREA_TOO_FEW_VERTICES:
            throw nb::value_error(
                "polygon needs at least 3 vertices to bound a region"
            );
        case SPAREA_OOM:
            throw std::bad_alloc();
        default:
            throw std::runtime_error("sparea: unknown error code");
    }
}

NB_MODULE(_nb, m) {
    m.doc() = "nanobind prototype binding for sparea — zero-copy (N, 3) numpy arrays.";

    m.def(
        "polygon_area",
        &polygon_area,
        "verts"_a,
        "Area in steradians of a spherical polygon. `verts` is a "
        "contiguous (N, 3) numpy array of unit xyz vectors."
    );
}
