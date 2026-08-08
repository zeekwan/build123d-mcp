// =========================================================
//  PROFILE FIT GAUGE
//  One plate, six apertures, six clearances.
//  Slide it on, find the one that feels right, use that
//  number forever.
// =========================================================

/* [YOUR CALIPER NUMBERS] --------------------------------- */
LEN     = 15.1;   // long axis of the cross-section
THK_END = 6.5;    // thickness at the ends
THK_MID = 7.0;    // thickness at the middle (the bulge)
CORNER_R = 0.4;   // corner radius. Guess; adjust to taste.

/* [THE TEST] --------------------------------------------- */
CLEARANCES = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35];
                  // per side, in mm

PLATE_T = 6;      // how much bore length each aperture samples
WALL    = 3;      // material between apertures
LABEL_H = 7;      // strip for the engraved numbers
LEAD_IN = 0.5;    // chamfer top and bottom of each bore.
                  // NOT a fudge — see note at the bottom.
TEXT_D  = 0.6;    // engrave depth

part = "detent_test";
// "gauge"       - the test plate. Print this first.
// "profile"     - a solid plug of the NOMINAL shape, so you can
//                 put calipers on it and check my maths against
//                 your measurements before burning a print.
// "section"     - flat 2D outline, for eyeballing the shape
// "sleeve"      - the actual wearable sleeve, once the gauge has
//                 told you your number. See SLEEVE section below.
// "detent_test" - just the snap-detent band, isolated into a
//                 short open-ended tube, to test the click
//                 feel before printing the full sleeve.

$fn = 96;
eps = 0.01;


// =========================================================
//  THE PROFILE
//  Two big arcs make the bulge: a chord of LEN with a
//  sagitta of (THK_MID - THK_END)/2 implies a radius of
//  about 114mm, so the faces are very slightly convex —
//  which is exactly what you measured.
// =========================================================
module juul_profile(clr = 0) {
    sag = (THK_MID - THK_END) / 2;
    c   = LEN / 2;
    R   = (c*c + sag*sag) / (2 * sag);
    yo  = THK_MID/2 - R;

    offset(r = clr)
      offset(r = CORNER_R) offset(r = -CORNER_R)
        intersection() {
            translate([0,  yo]) circle(r = R, $fn = 400);
            translate([0, -yo]) circle(r = R, $fn = 400);
            square([LEN, THK_MID + 4], center = true);
        }
}

// bore with a chamfer at both ends
module bore(clr) {
    W = THK_MID + 2*clr;
    // straight section
    translate([0, 0, -eps])
        linear_extrude(PLATE_T + 2*eps) juul_profile(clr);
    // bottom lead-in
    hull() {
        translate([0, 0, -eps])
            linear_extrude(eps) juul_profile(clr + LEAD_IN);
        translate([0, 0, LEAD_IN])
            linear_extrude(eps) juul_profile(clr);
    }
    // top lead-in
    hull() {
        translate([0, 0, PLATE_T - LEAD_IN])
            linear_extrude(eps) juul_profile(clr);
        translate([0, 0, PLATE_T])
            linear_extrude(eps + 0.01) juul_profile(clr + LEAD_IN);
    }
}


// =========================================================
//  GAUGE
// =========================================================
MAXC    = max(CLEARANCES);
N       = len(CLEARANCES);
PITCH   = LEN + 2*MAXC + WALL;
PLATE_L = N * PITCH + WALL;
PLATE_W = THK_MID + 2*MAXC + 2*WALL + LABEL_H;
HOLE_Y  = WALL + (THK_MID + 2*MAXC)/2;
TEXT_Y  = PLATE_W - LABEL_H/2;

module gauge() {
    difference() {
        cube([PLATE_L, PLATE_W, PLATE_T]);

        for (i = [0 : N-1]) {
            c = CLEARANCES[i];
            x = WALL + (LEN + 2*MAXC)/2 + i * PITCH;

            translate([x, HOLE_Y, 0]) bore(c);

            // engraved clearance, in hundredths
            translate([x, TEXT_Y, PLATE_T - TEXT_D])
                linear_extrude(TEXT_D + eps)
                    text(str(round(c * 100)), size = 4.5,
                         halign = "center", valign = "center",
                         font = "Liberation Sans:style=Bold");
        }
    }
}


// =========================================================
//  PART 2: THE SLEEVE
//  This is separate from everything above. The gauge exists
//  to find one number (SLEEVE_CLR below); once you have it,
//  this is the actual thing you wear.
// =========================================================

/* [YOUR WINNING NUMBER FROM THE GAUGE] -------------------- */
SLEEVE_CLR  = 0.25;  // <-- swap this for whatever clearance
                      //     felt right on the printed gauge.
                      //     placeholder until you test it.

/* [SLEEVE SHAPE] ------------------------------------------- */
SLEEVE_WALL = 1.0;   // wall thickness, all the way around
SLEEVE_H    = 100;   // total height
BASE_T      = 1.2;   // closed floor at the bottom — cavity
                      // stops short of z=0 by this much, so
                      // the device has something to rest on
                      // instead of an open-ended tube

BASE_FILLET_R     = 0.8;  // rounds the bottom OUTER edge only —
                           // the cavity stays crisp so fit is
                           // unaffected. Kept under BASE_T so it
                           // doesn't eat into the floor.
                           // NOT applied to the top: the top is
                           // where the device slides in, and
                           // rounding it the same way pinches the
                           // wall down to (SLEEVE_WALL - r) right
                           // at the rim — with r close to
                           // SLEEVE_WALL that's thin enough to
                           // print shut, sealing the opening.
BASE_FILLET_STEPS = 4;     // segments approximating the quarter-
                            // round; higher = smoother, slower

/* [THUMB WINDOW] --------------------------------------------
   Cut into the wide (LEN-axis) face, centered top to bottom. */
WIN_H  = 50;             // window height
WIN_W  = LEN;            // window width; runs edge-to-edge on
                          // the flat face, up to where it rounds
                          // into the side walls
WIN_Z0 = (SLEEVE_H - WIN_H) / 2;   // auto-centers it
WIN_ROUND_R = 2;          // fillet radius on the window opening,
                           // so the rim is smooth against a thumb

/* [DETENT / SNAP BUMP] ---------------------------------------
   The pod-removal dip on the juul: starts 78.13mm up, ends
   83mm up, .6mm deep per side. It's actually a small hexagonal
   recess, but for our purposes we approximate it as a smooth
   domed bump poking inward — roughly 5mm (LEN axis) wide,
   5mm tall, .5mm deep at its peak.

   IMPORTANT: this only lives on the two long flat faces (front
   +Y and back -Y). The real dip doesn't wrap around the rounded
   ends, so pinching those too (the old full-perimeter version)
   would grip the ends against a feature that isn't there.

   Implemented as a stretched sphere (ellipsoid) subtracted from
   the cavity — smooth and domed in every direction by
   construction, no separate ramp/plateau needed. */
DETENT_Z0    = 78.13;
DETENT_Z1    = 83;
DETENT_DEPTH = .4;   // inward bump, max depth at its peak.
                      // .5 was grabbing too tight; dropping to
                      // .4 while SLEEVE_CLR stays put at .25 —
                      // one variable at a time.
DETENT_TRANS = 1.5;   // extra height blended into the dome's
                       // taper — bigger = gentler entry, smaller
                       // = sharper "click"
DETENT_X     = 5;     // width of the bump along the LEN axis

// Domed bump on one long face. sign = +1 for front (+Y),
// -1 for back (-Y).
module detent_bump(sign) {
    zc = (DETENT_Z0 + DETENT_Z1) / 2;
    zh = (DETENT_Z1 - DETENT_Z0) + 2 * DETENT_TRANS;
    translate([0, sign * (THK_MID/2 + SLEEVE_CLR), zc])
        scale([DETENT_X/2, DETENT_DEPTH, zh/2])
            sphere(r = 1, $fn = 48);
}

/* [DETENT TEST PIECE] -----------------------------------------
   The snap feature is the part most worth checking before
   committing to a full 100mm print. This isolates just the
   detent band into its own short open-ended tube — slide the
   real device in from either end and feel whether it clicks
   in/out the way it should. */
DETENT_TEST_MARGIN = 15;  // straight tube above/below the
                           // detent band, for a decent grip length

DETENT_TEST_FILLET_R     = 0.4;  // rounds BOTH ends of this piece —
                                  // unlike the sleeve, this tube has
                                  // no closed floor, so both ends are
                                  // open and both compete with the
                                  // cavity the same way the sleeve's
                                  // top did. Kept well under
                                  // SLEEVE_WALL (leaves ~0.6mm rim)
                                  // so neither tip prints thin enough
                                  // to seal shut.
DETENT_TEST_FILLET_STEPS = 4;

module detent_test() {
    z0 = DETENT_Z0 - DETENT_TRANS - DETENT_TEST_MARGIN;
    z1 = DETENT_Z1 + DETENT_TRANS + DETENT_TEST_MARGIN;
    h  = z1 - z0;

    translate([0, 0, -z0])
    difference() {
        translate([0, 0, z0])
            filleted_extrude(SLEEVE_CLR + SLEEVE_WALL, h,
                              DETENT_TEST_FILLET_R, DETENT_TEST_FILLET_STEPS,
                              round_top = true);
        difference() {
            translate([0, 0, z0])
                linear_extrude(h) juul_profile(SLEEVE_CLR);
            detent_bump(1);
            detent_bump(-1);
        }
    }
}

// Inner bore: a straight run at SLEEVE_CLR from BASE_T up to
// the top (leaving a closed floor below it), with the two
// domed detent bumps subtracted where the pod-release dip sits.
module sleeve_cavity() {
    difference() {
        translate([0, 0, BASE_T])
            linear_extrude(SLEEVE_H - BASE_T) juul_profile(SLEEVE_CLR);
        detent_bump(1);
        detent_bump(-1);
    }
}

// rectangle with filleted corners, exact final size w x h
module rounded_rect(w, h, r) {
    offset(r = r)
        square([w - 2*r, h - 2*r], center = true);
}

// window through the front wall only (+Y side) — back wall
// and both side walls stay intact for stiffness. Rounded
// rim (WIN_ROUND_R) instead of a sharp-edged box, so it's
// smooth against a thumb.
module thumb_window() {
    depth = THK_MID/2 + SLEEVE_WALL + MAXC + 5;
    translate([0, 0, WIN_Z0 + WIN_H/2])
        rotate([-90, 0, 0])
            linear_extrude(depth)
                rounded_rect(WIN_W, WIN_H, WIN_ROUND_R);
}

// juul_profile(clr), extruded to height h, with the BOTTOM
// outer edge rounded over by radius r instead of left sharp.
// The top stays a flat, full-thickness, sharp-edged opening by
// default — that's the end you slide the device through on the
// real sleeve, so it keeps the full SLEEVE_WALL thickness all
// the way to the rim. Pass round_top = true (open-ended pieces
// like detent_test, with no floor to protect) to round that end
// too — but keep r well under the wall thickness on both ends,
// since ANY open end thins to (wall - r) right at the rim, and
// too thin prints shut instead of staying open.
// Same trick as the lead-in chamfers in bore() — thin slices of
// the offset profile, hulled together — just walked around a
// quarter circle (in steps) instead of straight-lined, so it
// reads as a true rounded edge rather than a bevel.
module filleted_extrude(clr, h, r, steps = 4, round_top = false) {
    top_h = round_top ? h - r : h;
    union() {
        // straight section, from the top of the bottom fillet
        // up to wherever the top starts (flat rim, or the start
        // of the top fillet)
        translate([0, 0, r])
            linear_extrude(top_h - r) juul_profile(clr);

        // bottom edge, always
        for (i = [0 : steps - 1]) {
            t0 = i * 90 / steps;
            t1 = (i + 1) * 90 / steps;
            za0 = r * (1 - sin(t0));  za1 = r * (1 - sin(t1));
            in0 = r * (1 - cos(t0));  in1 = r * (1 - cos(t1));

            hull() {
                translate([0, 0, za0])
                    linear_extrude(eps) juul_profile(clr - in0);
                translate([0, 0, za1])
                    linear_extrude(eps) juul_profile(clr - in1);
            }
            // top edge, mirrored, only if requested
            if (round_top) {
                hull() {
                    translate([0, 0, h - za0])
                        linear_extrude(eps) juul_profile(clr - in0);
                    translate([0, 0, h - za1])
                        linear_extrude(eps) juul_profile(clr - in1);
                }
            }
        }
    }
}

module sleeve() {
    difference() {
        filleted_extrude(SLEEVE_CLR + SLEEVE_WALL, SLEEVE_H,
                          BASE_FILLET_R, BASE_FILLET_STEPS);
        sleeve_cavity();
        thumb_window();
    }
}


// =========================================================
//  OUTPUT
// =========================================================
if (part == "gauge") gauge();
else if (part == "profile")
    linear_extrude(10) juul_profile(0);
else if (part == "section")
    linear_extrude(1) juul_profile(0);
else if (part == "sleeve") sleeve();
else if (part == "detent_test") detent_test();

echo(str("plate ", PLATE_L, " x ", PLATE_W, " x ", PLATE_T, "mm"));
echo(str("apertures: ", LEN, " x ", THK_MID, " nominal, plus ",
         CLEARANCES, " per side"));
if (part == "sleeve")
    echo(str("sleeve: ", SLEEVE_H, "mm tall, ", SLEEVE_WALL,
             "mm wall, ", BASE_T, "mm base, clearance ", SLEEVE_CLR,
             ", detent ", DETENT_Z0, "-", DETENT_Z1, "mm"));
if (part == "detent_test")
    echo(str("detent test: ", (DETENT_Z1 - DETENT_Z0) + 2*DETENT_TRANS
             + 2*DETENT_TEST_MARGIN, "mm tall, detent band ",
             DETENT_Z0, "-", DETENT_Z1, "mm from the bottom"));


// =========================================================
//  NOTES
//
//  PRINT IT FLAT, bores vertical. That matters — it's the
//  same orientation the real holder's pocket will print in,
//  so the number you find here transfers directly. Print it
//  on its side and the result is meaningless.
//
//  WHY THE LEAD-IN CHAMFER IS NOT CHEATING
//  Your first layer squishes outward (elephant foot), which
//  pinches the bottom 0.2-0.3mm of every bore inward. Left
//  alone it would make all six apertures read tighter than
//  they are and you'd pick the wrong number. The 0.5mm
//  chamfer removes exactly that corrupted layer. Keep it.
//
//  READ IT WITH YOUR HANDS, not calipers. Slide each
//  aperture the full length of the device. You want:
//    - too tight: binds, or needs force
//    - right: slides with light drag, no rattle
//    - too loose: audible rattle when you shake it
//  For a holder you drop the thing into, go one step looser
//  than "right". For a friction holder that grips it, go one
//  tighter.
//
//  CHECK MY SHAPE FIRST. part = "profile" gives you a 10mm
//  solid plug of the nominal cross-section. Put calipers on
//  it: should read 15.1 across, 7.0 at the middle of the
//  narrow axis, 6.5 near the ends. If that's wrong, the
//  gauge is wrong too and no clearance will save it.
//
//  THE BULGE IS THE CONTROLLING DIMENSION. A pocket sized
//  to 6.5 won't accept a 7.0 middle at all. Everything here
//  is built off THK_MID for that reason; THK_END only
//  determines how curved the faces are.
//
//  IF ALL SIX ARE TIGHT ..... add 0.40 and 0.45 to the list
//  IF ALL SIX ARE LOOSE ..... your CORNER_R is probably too
//                             small, or the measured LEN is
//                             over. Re-measure across the
//                             widest point.
// =========================================================
