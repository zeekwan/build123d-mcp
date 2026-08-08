"""Isolated detent-band test tube for the juul-sleeve project.

Redesigned in build123d from the `detent_test` module in
personal/references/juul_sleeve.scad (OpenSCAD) — not a literal port.
Where OpenSCAD had to approximate (manual quarter-circle-hull rim fillets,
polygon offset for corner rounding), this uses real OCCT operations
(ThreePointArc, fillet, a non-uniform-scaled sphere for the ellipsoid
detent bumps) instead. Clearance is also per-axis here (SLEEVE_CLR_X vs
SLEEVE_CLR_Y) — the OpenSCAD source only had one uniform SLEEVE_CLR.

Paste into build123d-mcp's execute(), or run standalone with build123d
installed (drop the show() call).
"""

from build123d import *

# --- caliper numbers (source of truth: personal/references/juul_sleeve.scad) ---
LEN = 15.1  # long axis of the cross-section
THK_END = 6.5  # thickness at the ends
THK_MID = 7.0  # thickness at the middle (the bulge)
CORNER_R = 0.4  # corner radius

SLEEVE_CLR_X = 0.25  # fit clearance on the short end walls (LEN axis)
SLEEVE_CLR_Y = 0.15  # fit clearance on the long flat walls (THK axis) —
                      # was 0.25 like SLEEVE_CLR_X; the long walls felt too
                      # loose on the printed detent_test, tightened by
                      # 0.1mm/side here while the end walls stay put
SLEEVE_WALL = 1.0  # wall thickness

DETENT_Z0 = 78.13  # pod-release dip, start height on the real sleeve
DETENT_Z1 = 83  # pod-release dip, end height
DETENT_TRANS = 1.5  # extra height blended into the dome's taper
DETENT_TEST_MARGIN = 15  # straight tube above/below the detent band
DETENT_TEST_FILLET_R = 0.4  # rounds both open ends of this test piece
DETENT_DEPTH = 0.4  # inward bump depth at its peak
DETENT_X = 5  # bump width along the LEN axis


def juul_profile(clr_x: float = 0.0, clr_y: float = 0.0):
    """The bulged-stadium cross-section: two large-radius arcs (the very
    slightly convex long faces) connecting flat short end walls, with the
    4 corners filleted.

    clr_x/clr_y grow the defining half-extents directly (LEN/2 +/- clr_x,
    THK/2 +/- clr_y) rather than via a generic offset() on the finished
    face — that's what makes independent per-axis clearance possible, and
    as a side effect the corner radius stays exactly CORNER_R regardless
    of clearance (a uniform offset would instead grow it to CORNER_R+clr)."""
    p_tr = (LEN / 2 + clr_x, THK_END / 2 + clr_y)
    p_tm = (0, THK_MID / 2 + clr_y)
    p_tl = (-LEN / 2 - clr_x, THK_END / 2 + clr_y)
    p_bl = (-LEN / 2 - clr_x, -THK_END / 2 - clr_y)
    p_bm = (0, -THK_MID / 2 - clr_y)
    p_br = (LEN / 2 + clr_x, -THK_END / 2 - clr_y)
    with BuildLine() as ln:
        ThreePointArc(p_tr, p_tm, p_tl)
        Line(p_tl, p_bl)
        ThreePointArc(p_bl, p_bm, p_br)
        Line(p_br, p_tr)
    with BuildSketch(Plane.XY) as sk:
        add(ln.line)
        make_face()
        fillet(sk.vertices(), radius=CORNER_R)
    return sk.sketch


def detent_bump(sign: int, zc_local: float, zh: float):
    """A domed inward bump on one long face: a unit sphere, non-uniformly
    scaled into an ellipsoid (build123d's transform_geometry, not a raw
    OCCT call), positioned at the pod-release-dip height on the +Y/-Y face."""
    with BuildPart() as bp:
        add(Sphere(radius=1))
    sphere = bp.part
    scale = Matrix(
        [
            [DETENT_X / 2, 0, 0, 0],
            [0, DETENT_DEPTH, 0, 0],
            [0, 0, zh / 2, 0],
            [0, 0, 0, 1],
        ]
    )
    ellipsoid = sphere.transform_geometry(scale)
    return ellipsoid.moved(Location((0, sign * (THK_MID / 2 + SLEEVE_CLR_Y), zc_local)))


def build_detent_test():
    z0 = DETENT_Z0 - DETENT_TRANS - DETENT_TEST_MARGIN
    z1 = DETENT_Z1 + DETENT_TRANS + DETENT_TEST_MARGIN
    h = z1 - z0
    zc_local = (DETENT_Z0 + DETENT_Z1) / 2 - z0
    zh = (DETENT_Z1 - DETENT_Z0) + 2 * DETENT_TRANS

    outer_face = juul_profile(SLEEVE_CLR_X + SLEEVE_WALL, SLEEVE_CLR_Y + SLEEVE_WALL)
    inner_face = juul_profile(SLEEVE_CLR_X, SLEEVE_CLR_Y)

    with BuildPart() as outer_bp:
        add(extrude(outer_face, amount=h))
        rim_edges = outer_bp.faces().filter_by(Axis.Z).edges()
        fillet(rim_edges, radius=DETENT_TEST_FILLET_R)
    outer_solid = outer_bp.part

    with BuildPart() as inner_bp:
        add(extrude(inner_face, amount=h))
    cavity_solid = inner_bp.part

    bump_front = detent_bump(1, zc_local, zh)
    bump_back = detent_bump(-1, zc_local, zh)
    reduced_cavity = cavity_solid - bump_front - bump_back

    return outer_solid - reduced_cavity


result = build_detent_test()
show(result, name="detent_test")
