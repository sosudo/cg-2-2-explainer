"""Manim scenes for the notched-prism unfolding explainer.

Render with build.sh; every scene is timed against the Kokoro narration in audio/.
"""
import json
import math
import random
from pathlib import Path

import numpy as np
from manim import *
from shapely.geometry import Polygon as SPoly
from shapely.ops import unary_union

import geometry as G

ROOT = Path(__file__).parent
DUR = json.loads((ROOT / "audio" / "durations.json").read_text())

config.background_color = "#0e1117"
FONT = "DejaVu Sans"
LID = "#4f86c6"
LID2 = "#3c6aa3"
WALL = "#d9a441"
WALL2 = "#c08a2c"
CUT = "#ff4d4d"
RIM = "#4cd97b"
NOTCH = "#ff9f43"
ACCENT = "#ffd166"
SOFT = "#9aa4b2"

# Shapes used throughout.
M, RADIUS, OPENING, H = 10, 2.0, 60.0, 1.0
YES_POLY, _ = G.notched_polygon(M, RADIUS, OPENING, set(range(1, M)), rotate_deg=-108)
SAW_POLY, _ = G.notched_polygon(M, RADIUS, OPENING, None, rotate_deg=-108)
CONVEX10, _ = G.notched_polygon(M, RADIUS, OPENING, set(), rotate_deg=-108)


def T(s, size=34, color=WHITE, **kw):
    return Text(s, font=FONT, font_size=size, color=color, **kw)


def header(s):
    return T(s, 26, SOFT).to_corner(UL, buff=0.35)


def p3(xy, z=0.0):
    return np.array([xy[0], xy[1], z])


def poly2d(pts, **kw):
    return Polygon(*[p3(p) for p in pts], **kw)


def angle_kinds(poly):
    ang = G.interior_angles(poly)
    return ["reflex" if a > np.pi else "convex" for a in ang]


def edge_lines(poly, colors, width=6):
    n = len(poly)
    return VGroup(*[
        Line(p3(poly[i]), p3(poly[(i + 1) % n]), color=colors[i], stroke_width=width)
        for i in range(n)
    ])


def edge_colors(poly):
    rims = set(G.rim_edges(poly))
    return [RIM if i in rims else NOTCH for i in range(len(poly))]


def to_shapely(mpoly_pts):
    return SPoly(mpoly_pts)


def shapely_to_mobs(geom, **kw):
    geoms = getattr(geom, "geoms", [geom])
    out = VGroup()
    for g in geoms:
        if g.is_empty or g.area < 1e-6:
            continue
        out.add(Polygon(*[p3(c) for c in list(g.exterior.coords)[:-1]], **kw))
    return out


def corner_arcs(c, pa, pb, r, **kw):
    """Arcs at corner c between rays to pa and pb: (small wedge, reflex wedge)."""
    ta = np.arctan2(pa[1] - c[1], pa[0] - c[0])
    tb = np.arctan2(pb[1] - c[1], pb[0] - c[0])
    d = (tb - ta + PI) % TAU - PI
    small = Arc(radius=r, start_angle=ta, angle=d, arc_center=p3(c), **kw)
    big = Arc(radius=r, start_angle=ta, angle=d - np.sign(d) * TAU, arc_center=p3(c), **kw)
    return small, big


def fan_piece(kind, start, angle_deg, center, r=1.6, **kw):
    """A face around a corner: the lid as a wedge, a wall as a square."""
    a0 = start
    if kind == "lid":
        return Sector(radius=r, angle=angle_deg * DEGREES, start_angle=a0,
                      arc_center=center, fill_color=LID, fill_opacity=0.75,
                      stroke_color=WHITE, stroke_width=2, **kw)
    s = r * 0.8
    u = np.array([np.cos(a0), np.sin(a0), 0])
    v = np.array([np.cos(a0 + PI / 2), np.sin(a0 + PI / 2), 0])
    return Polygon(center, center + s * u, center + s * (u + v), center + s * v,
                   fill_color=WALL, fill_opacity=0.75, stroke_color=WHITE,
                   stroke_width=2, **kw)


def build_fan(spec, center, r=1.6):
    """spec: list of (kind, degrees). Returns pieces laid consecutively from angle 0."""
    pieces, a = VGroup(), 0.0
    for kind, deg in spec:
        pieces.add(fan_piece(kind, a, deg, center, r))
        a += deg * DEGREES
    return pieces


def fan_overlap(pieces):
    """Red highlight of the region covered twice by a fan."""
    shapes = []
    for p in pieces:
        pts = np.array(p.get_anchors())[:, :2]
        shapes.append(SPoly(pts).buffer(0))
    over = []
    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            inter = shapes[i].intersection(shapes[j])
            if inter.area > 1e-4:
                over.append(inter)
    if not over:
        return VGroup()
    return shapely_to_mobs(unary_union(over), fill_color=CUT, fill_opacity=0.85, stroke_width=0)


# --------------------------------------------------------------- base class
class Narrated:
    def seg(self, key):
        self.add_sound(str(ROOT / "audio" / f"{key}.wav"))
        self._t0, self._dur, self._key = self.renderer.time, DUR[key], key

    def left(self, pad=0.0):
        return self._t0 + self._dur - self.renderer.time - pad

    def done(self, pad=0.35):
        rem = self.left() + pad
        if rem > 0.02:
            self.wait(rem)
        elif rem < -0.05:
            print(f"WARNING: segment {self._key} overran by {-rem:.2f}s")


class Scene2D(Narrated, Scene):
    pass


class Scene3D(Narrated, ThreeDScene):
    pass


# ------------------------------------------------------------- 3D folding
class Folding(VGroup):
    """Faces of a polyhedron that open along an Unfolding as trackers move."""

    def __init__(self, U, colors, groups, opacity=0.9, stroke=1.5):
        super().__init__()
        self.U = U
        self.trackers = {g: ValueTracker(0) for g in set(groups.values())}
        self.groups = groups
        self.polys = []
        for f in range(len(U.P.faces)):
            pts = U.face_points(f, self.t)
            poly = Polygon(*pts, fill_color=colors[f], fill_opacity=opacity,
                           stroke_color=WHITE, stroke_width=stroke)
            poly.set_shade_in_3d(True)
            self.polys.append(poly)
            self.add(poly)
        self.add_updater(lambda m: m.refresh())

    def t(self, f):
        g = self.groups.get(f)
        return 0.0 if g is None else self.trackers[g].get_value()

    def refresh(self):
        for f, poly in enumerate(self.polys):
            pts = self.U.face_points(f, self.t)
            poly.set_points_as_corners([*pts, pts[0]])


def prism_colors(n):
    cols = [LID2, LID]
    cols += [WALL if i % 2 == 0 else WALL2 for i in range(n)]
    return cols


# =================================================================== SCENES
class S01_Intro(Scene3D):
    def construct(self):
        self.set_camera_orientation(phi=65 * DEGREES, theta=-50 * DEGREES, zoom=1.6)
        P = G.cube(2.0)
        hinges = [(0, 2), (0, 3), (0, 4), (0, 5), (3, 1)]
        hinge_edges = set()
        for a, b in hinges:
            hinge_edges |= {e for e, fs in P.edge_faces.items() if set(fs) == {a, b}}
        cuts = [tuple(e) for e in P.edges if e not in hinge_edges]
        U = G.Unfolding(P, cuts, root=0)
        cols = ["#e76f51", "#f4a261", "#e9c46a", "#2a9d8f", "#4f86c6", "#9b5de5"]
        groups = {f: "a" for f in range(6) if f != 0}
        groups[1] = "b"
        box = Folding(U, cols, groups)

        self.seg("intro_box")
        self.play(FadeIn(box), run_time=1.2)
        cut_lines = VGroup(*[Line(P.V[a], P.V[b], color=CUT, stroke_width=7)
                             for a, b in (tuple(e) for e in cuts)])
        self.play(Create(cut_lines), run_time=1.6)
        self.play(FadeOut(cut_lines), run_time=0.4)
        self.play(box.trackers["a"].animate.set_value(1),
                  box.trackers["b"].animate.set_value(1), run_time=3.0)
        self.move_camera(phi=0, theta=-90 * DEGREES, zoom=0.9, run_time=1.8)
        lab = T("an unfolding (a “net”)", 30, ACCENT).to_edge(DOWN)
        self.add_fixed_in_frame_mobjects(lab)
        self.play(FadeIn(lab), run_time=0.5)
        self.done()

        self.seg("intro_goal")
        title = T("Unfolding dented boxes", 52, WHITE)
        sub = T("one family, two answers, one fast test", 30, SOFT)
        c1 = T("① some shapes say YES, some say NO", 30, RIM)
        c2 = T("② decide which, provably faster than brute force", 30, ACCENT)
        card = VGroup(title, sub, c1, c2).arrange(DOWN, buff=0.35)
        c1.shift(0.25 * DOWN)
        c2.shift(0.25 * DOWN)
        self.add_fixed_in_frame_mobjects(card)
        card.set_opacity(0)
        self.play(FadeOut(box), FadeOut(lab), run_time=0.8)
        self.play(title.animate.set_opacity(1), sub.animate.set_opacity(1), run_time=1.0)
        self.wait(2.5)
        self.play(c1.animate.set_opacity(1), run_time=0.8)
        self.wait(1.5)
        self.play(c2.animate.set_opacity(1), run_time=0.8)
        self.done()
        self.play(FadeOut(card), run_time=0.6)


class S02_Polytope(Scene3D):
    def construct(self):
        self.set_camera_orientation(phi=68 * DEGREES, theta=-60 * DEGREES, zoom=0.85)
        hdr = header("Vocabulary")
        self.add_fixed_in_frame_mobjects(hdr)

        self.seg("def_polytope")
        cube = G.cube(1.8)
        pyr = G.square_pyramid(1.9, 1.7)
        tri = np.array([[0, 0], [1.6, 0], [0.5, 1.2]])
        tri = tri - tri.mean(0)
        pri = G.prism(tri, 1.8)

        def solid(P, shift, col1, col2):
            g = VGroup()
            for fi, f in enumerate(P.faces):
                poly = Polygon(*(P.V[f] + shift), fill_color=col1 if fi % 2 else col2,
                               fill_opacity=0.9, stroke_color=WHITE, stroke_width=1.5)
                poly.set_shade_in_3d(True)
                g.add(poly)
            return g

        s1 = solid(cube, np.array([-3.6, 0, 0]), "#e76f51", "#f4a261")
        s2 = solid(pyr, np.array([0, 0, -0.85]), "#2a9d8f", "#3fbfae")
        s3 = solid(pri, np.array([3.6, 0, -0.9]), LID, LID2)
        self.play(FadeIn(s1), FadeIn(s2), FadeIn(s3), run_time=1.5)
        names = VGroup(T("cube", 28), T("pyramid", 28), T("prism", 28))
        for nm, x in zip(names, (-4.3, 0, 4.3)):
            nm.move_to([x, -2.9, 0])
        self.add_fixed_in_frame_mobjects(names)
        self.play(FadeIn(names), run_time=0.6)
        self.wait(1.0)
        # face / edge / vertex on the cube
        f_hi = s1[1].copy().set_fill(ACCENT, 0.95)
        e_hi = Line(cube.V[4] + [-3.6, 0, 0], cube.V[5] + [-3.6, 0, 0], color=CUT, stroke_width=9)
        v_hi = Dot3D(cube.V[7] + [-3.6, 0, 0], radius=0.12, color=RIM)
        lf, le, lv = T("face", 30, ACCENT), T("edge", 30, CUT), T("vertex", 30, RIM)
        legend = VGroup(lf, le, lv).arrange(RIGHT, buff=0.8).to_edge(UP, buff=0.9)
        self.add_fixed_in_frame_mobjects(legend)
        legend.set_opacity(0)
        self.play(FadeIn(f_hi), lf.animate.set_opacity(1), run_time=1.0)
        self.wait(1.2)
        self.play(Create(e_hi), le.animate.set_opacity(1), run_time=1.0)
        self.wait(1.0)
        self.play(FadeIn(v_hi), lv.animate.set_opacity(1), run_time=1.0)
        spin = max(0.5, self.left(0.3))
        cube_grp = VGroup(s1, f_hi, e_hi, v_hi)
        self.play(Rotate(cube_grp, PI / 2, axis=OUT, about_point=cube_grp.get_center()),
                  Rotate(s2, PI / 2, axis=OUT, about_point=s2.get_center()),
                  Rotate(s3, PI / 2, axis=OUT, about_point=s3.get_center()),
                  run_time=spin, rate_func=smooth)
        self.done()
        self.play(*[FadeOut(m) for m in (s1, s2, s3, names, f_hi, e_hi, v_hi, legend)], run_time=0.8)


class S03_Convex(Scene2D):
    def construct(self):
        self.add(header("Vocabulary"))
        self.seg("def_convex")
        convex = poly2d(CONVEX10 * 0.9, fill_color=LID, fill_opacity=0.7, stroke_color=WHITE).shift(3.3 * LEFT)
        dent_pts = np.array([[-1.6, -1.4], [1.6, -1.4], [1.6, 1.4], [0.5, 1.4], [0, 0.1], [-0.5, 1.4], [-1.6, 1.4]])
        dented = poly2d(dent_pts, fill_color=WALL, fill_opacity=0.7, stroke_color=WHITE).shift(3.3 * RIGHT)
        l1 = T("convex: no dents", 30, RIM).next_to(convex, DOWN, buff=0.5)
        l2 = T("not convex: has a dent", 30, NOTCH).next_to(dented, DOWN, buff=0.5)
        self.play(FadeIn(convex), FadeIn(dented), run_time=1.0)
        self.play(FadeIn(l1), FadeIn(l2), run_time=0.6)
        wrap1 = Circle(radius=2.6, color=ACCENT, stroke_width=5).move_to(convex)
        wrap2 = Circle(radius=2.6, color=ACCENT, stroke_width=5).move_to(dented)
        self.play(Create(wrap1), Create(wrap2), run_time=0.8)
        hull1 = convex.copy().set_fill(opacity=0).set_stroke(ACCENT, 5)
        hull2 = poly2d(dent_pts[[0, 1, 2, 3, 5, 6]], color=ACCENT, stroke_width=5).shift(3.3 * RIGHT)
        self.play(Transform(wrap1, hull1), Transform(wrap2, hull2), run_time=2.2)
        gap = poly2d(dent_pts[[3, 4, 5]], fill_color=ACCENT, fill_opacity=0.3, stroke_width=0).shift(3.3 * RIGHT)
        note = T("shrink wrap bridges the dent", 26, ACCENT).next_to(dented, UP, buff=0.4)
        self.play(FadeIn(gap), FadeIn(note), run_time=0.8)
        self.done()
        self.play(*[FadeOut(m) for m in self.mobjects if m is not self.mobjects[0]], run_time=0.6)


class S04_Unfold(Scene3D):
    def construct(self):
        self.set_camera_orientation(phi=62 * DEGREES, theta=-55 * DEGREES, zoom=1.15)
        hdr = header("Vocabulary")
        self.add_fixed_in_frame_mobjects(hdr)
        P = G.square_pyramid(2.2, 1.8)
        cuts = [(0, 4), (1, 4), (2, 4), (3, 4)]
        U = G.Unfolding(P, cuts, root=0)
        cols = ["#2a9d8f", "#e76f51", "#f4a261", "#e9c46a", "#9b5de5"]
        fold = Folding(U, cols, {f: "a" for f in range(1, 5)})
        self.seg("def_unfold")
        self.play(FadeIn(fold), run_time=1.0)
        cut_lines = VGroup(*[Line(P.V[a], P.V[b], color=CUT, stroke_width=7) for a, b in cuts])
        rule1 = T("✂ cut only along edges", 30, CUT)
        rule2 = T("⟶ one connected flat piece", 30, ACCENT)
        rules = VGroup(rule1, rule2).arrange(DOWN, aligned_edge=LEFT).to_corner(UR, buff=0.5)
        self.add_fixed_in_frame_mobjects(rules)
        rules.set_opacity(0)
        self.play(Create(cut_lines), rule1.animate.set_opacity(1), run_time=1.8)
        self.wait(1.0)
        self.play(FadeOut(cut_lines), run_time=0.4)
        self.play(fold.trackers["a"].animate.set_value(1), run_time=3.2)
        self.play(rule2.animate.set_opacity(1), run_time=0.6)
        self.move_camera(phi=20 * DEGREES, theta=-90 * DEGREES, run_time=1.6)
        self.done()
        self.play(FadeOut(fold), FadeOut(rules), run_time=0.6)


class S05_Overlap(Scene2D):
    def construct(self):
        self.add(header("Vocabulary"))
        self.seg("def_overlap")
        n = len(SAW_POLY)
        Pz = G.prism(SAW_POLY, H)
        U = G.strip_unfolding(Pz, n, 3, (3 + n // 2) % n)
        flat = U.flat_2d()
        sc = 0.5
        center = np.array([0.0, 0.5])
        faces = VGroup()
        for f, pts in flat.items():
            col = LID if f in (0, 1) else (WALL if f % 2 else WALL2)
            faces.add(poly2d((pts - center) * sc, fill_color=col, fill_opacity=0.75,
                             stroke_color=WHITE, stroke_width=1.2))
        faces.move_to(ORIGIN + 0.2 * DOWN)
        shift = faces.get_center()
        strip = unary_union([SPoly(flat[f]).buffer(0) for f in flat if f >= 2])
        lids = [SPoly(flat[0]), SPoly(flat[1])]
        over = unary_union([l.intersection(strip) for l in lids])
        raw_center = (np.vstack(list(flat.values())) - center) * sc
        offset = shift - p3(0.5 * (raw_center.min(0) + raw_center.max(0)))
        red = shapely_to_mobs(over, fill_color=CUT, fill_opacity=0.95, stroke_color=CUT, stroke_width=2)
        for mob in red:
            mob.points = (mob.points - p3(center)) * sc
            mob.points[:, 2] = 0
            mob.shift(offset)
        self.play(LaggedStart(*[FadeIn(f) for f in faces], lag_ratio=0.03), run_time=2.0)
        self.wait(1.2)
        self.play(FadeIn(red), Flash(red.get_center(), color=CUT, flash_radius=0.8), run_time=1.0)
        self.play(Indicate(red, color=CUT, scale_factor=1.15), run_time=1.0)
        bad = T("overlap → not allowed", 32, CUT).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(bad), run_time=0.6)
        self.done()
        self.play(FadeOut(faces), FadeOut(red), FadeOut(bad), run_time=0.6)

        self.seg("def_problem")
        box = RoundedRectangle(width=12.0, height=4.6, corner_radius=0.3, color=ACCENT)
        l1 = T("INPUT:  a polytope", 34)
        l2 = T("QUESTION:  can we cut along edges so it unfolds", 32)
        l3 = T("into ONE flat piece with NO overlaps?", 32)
        l4 = VGroup(T("OUTPUT:", 34), T("YES", 40, RIM), T("or", 34), T("NO", 40, CUT)).arrange(RIGHT, buff=0.35)
        txt = VGroup(l1, l2, l3, l4).arrange(DOWN, buff=0.4, aligned_edge=LEFT)
        l3.shift(0.9 * RIGHT)
        txt.move_to(box)
        self.play(Create(box), run_time=0.8)
        for m in (l1, VGroup(l2, l3), l4):
            self.play(FadeIn(m, shift=0.2 * UP), run_time=0.7)
            self.wait(1.4)
        self.done()
        self.play(FadeOut(VGroup(box, txt)), run_time=0.6)


# ----------------------------------------------------------- spanning trees
CUBE = G.cube(2.0)
CUBE_EDGES = [tuple(sorted(e)) for e in CUBE.edges]


def schlegel(v):
    x, y, z = v & 1, (v >> 1) & 1, v >> 2
    s = 2.0 if z else 0.85
    return np.array([(2 * x - 1) * s, (2 * y - 1) * s, 0])


def oblique(v):
    x, y, z = v & 1, (v >> 1) & 1, v >> 2
    return np.array([(2 * x - 1) * 1.3 + 0.75 * (2 * y - 1), (2 * z - 1) * 1.3 + 0.55 * (2 * y - 1), 0])


def cube_graph(pos, scale=1.0, shift=ORIGIN, ecol=SOFT, width=4, dot=0.09):
    dots = VGroup(*[Dot(pos(v) * scale + shift, radius=dot, color=WHITE, z_index=2) for v in range(8)])
    lines = {e: Line(pos(e[0]) * scale + shift, pos(e[1]) * scale + shift, color=ecol, stroke_width=width)
             for e in CUBE_EDGES}
    return dots, lines


def random_tree(rng):
    edges = CUBE_EDGES[:]
    rng.shuffle(edges)
    parent = list(range(8))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    tree = []
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            tree.append((a, b))
    return tree


def net_mob(tree, width, show_edges=True):
    U = G.Unfolding(CUBE, tree, root=0)
    flat = U.flat_2d()
    cut = {frozenset(e) for e in tree}
    allp = np.vstack(list(flat.values()))
    lo, hi = allp.min(0), allp.max(0)
    sc = width / max(hi[0] - lo[0], hi[1] - lo[1])
    mid = (lo + hi) / 2
    cols = ["#e76f51", "#f4a261", "#e9c46a", "#2a9d8f", "#4f86c6", "#9b5de5"]
    g = VGroup()
    edges = VGroup()
    for f, pts in flat.items():
        q = (pts - mid) * sc
        g.add(poly2d(q, fill_color=cols[f], fill_opacity=0.85, stroke_width=0))
        fv = CUBE.faces[f]
        for k in range(len(fv)):
            e = frozenset((fv[k], fv[(k + 1) % len(fv)]))
            a, b = p3(q[k]), p3(q[(k + 1) % len(q)])
            if e in cut:
                edges.add(Line(a, b, color=CUT, stroke_width=4))
            else:
                edges.add(DashedLine(a, b, color=WHITE, stroke_width=2, dash_length=0.08))
    if show_edges:
        g.add(edges)
    return g


CROSS_TREE = None


def cross_tree():
    hinges = [(0, 2), (0, 3), (0, 4), (0, 5), (3, 1)]
    hinge_edges = set()
    for a, b in hinges:
        hinge_edges |= {e for e, fs in CUBE.edge_faces.items() if set(fs) == {a, b}}
    return [tuple(sorted(e)) for e in CUBE.edges if e not in hinge_edges]


class S06_Graph(Scene2D):
    def construct(self):
        self.add(header("Which edges get cut?"))
        self.seg("st_graph")
        dots, lines = cube_graph(oblique)
        self.play(*[Create(l) for l in lines.values()], run_time=1.5)
        self.play(FadeIn(dots), run_time=0.6)
        self.wait(1.0)
        dots2, lines2 = cube_graph(schlegel, ecol=WHITE)
        self.play(*[Transform(dots[i], dots2[i]) for i in range(8)],
                  *[Transform(lines[e], lines2[e]) for e in CUBE_EDGES], run_time=2.2)
        lab1 = T("vertex = town", 30, RIM).to_corner(UR, buff=0.6)
        lab2 = T("edge = road", 30, ACCENT).next_to(lab1, DOWN, aligned_edge=LEFT)
        self.play(FadeIn(lab1), dots.animate.set_color(RIM), run_time=0.8)
        self.play(FadeIn(lab2), *[l.animate.set_color(ACCENT) for l in lines.values()], run_time=0.8)
        self.done()
        self.play(dots.animate.set_color(WHITE), *[l.animate.set_color(SOFT) for l in lines.values()],
                  FadeOut(lab1), FadeOut(lab2), run_time=0.6)
        graph = VGroup(dots, *lines.values())

        # ---- rules
        self.seg("st_rules")
        self.play(graph.animate.scale(0.7).to_edge(RIGHT, buff=0.8), run_time=0.8)
        # party hat
        apex = np.array([-4.2, 1.6, 0])
        base_c = np.array([-4.2, -0.8, 0])
        ell = Ellipse(width=2.4, height=0.6, color=WHITE).move_to(base_c)
        hat = VGroup(
            Polygon(apex, base_c + 1.2 * LEFT, base_c + 1.2 * RIGHT, fill_color="#9b5de5", fill_opacity=0.8, stroke_width=0),
            ell.copy().set_fill("#7a3fc4", 0.8),
            Line(apex, base_c + 1.2 * LEFT), Line(apex, base_c + 1.2 * RIGHT), Dot(apex, color=ACCENT))
        hat_lab = T("party hat = a pointy corner", 26, SOFT).next_to(ell, DOWN, buff=0.4)
        self.play(FadeIn(hat), FadeIn(hat_lab), run_time=0.8)
        slit = DashedLine(apex, base_c + 0.3 * DOWN, color=CUT, stroke_width=5)
        self.play(Create(slit), run_time=0.8)
        flat = Sector(radius=2.0, angle=250 * DEGREES, start_angle=-215 * DEGREES,
                      arc_center=apex + 0.5 * DOWN, fill_color="#9b5de5", fill_opacity=0.8, stroke_color=WHITE)
        self.play(ReplacementTransform(VGroup(hat, slit), flat), run_time=1.4)
        r1 = T("① cuts reach every corner", 28, RIM).to_edge(DOWN, buff=1.1).shift(2.5 * LEFT)
        self.play(FadeIn(r1), run_time=0.5)
        self.wait(1.0)
        self.play(FadeOut(flat), FadeOut(hat_lab), run_time=0.5)
        # loop cuts off a piece
        loop = [(0, 1), (1, 3), (2, 3), (0, 2)]
        loop_lines = VGroup(*[lines[e].copy().set_color(CUT).set_stroke(width=8) for e in loop])
        self.play(Create(loop_lines), run_time=1.0)
        piece = Polygon(*[dots[v].get_center() for v in (0, 1, 3, 2)], fill_color=CUT, fill_opacity=0.5, stroke_width=0)
        self.play(FadeIn(piece), run_time=0.4)
        self.play(piece.animate.shift(3.6 * LEFT + 0.3 * DOWN).rotate(0.4), run_time=1.0)
        r2 = T("② no loops (a loop cuts a piece off)", 28, CUT).next_to(r1, DOWN, aligned_edge=LEFT)
        self.play(FadeIn(r2), run_time=0.5)
        self.play(FadeOut(piece), FadeOut(loop_lines), run_time=0.6)
        r3 = T("⇒ cut edges form a SPANNING TREE", 32, ACCENT).to_edge(UP, buff=1.0).shift(2 * LEFT)
        self.play(Write(r3), run_time=1.0)
        self.done()
        self.play(FadeOut(VGroup(r1, r2, r3)), graph.animate.scale(1 / 0.7).move_to(ORIGIN), run_time=0.8)

        # ---- definition
        self.seg("st_define")
        tree = cross_tree()
        tdef = T("spanning tree: connects every vertex, no loops", 30, ACCENT).to_edge(UP, buff=0.9)
        self.play(FadeIn(tdef), run_time=0.7)
        tl = VGroup(*[lines[e].copy().set_color(ACCENT).set_stroke(width=9) for e in tree])
        self.play(LaggedStart(*[Create(l) for l in tl], lag_ratio=0.3), run_time=2.4)
        self.play(*[Indicate(d, color=RIM) for d in dots], run_time=1.0)
        # unique route between two towns
        adj = {v: [] for v in range(8)}
        for a, b in tree:
            adj[a].append(b)
            adj[b].append(a)
        start, goal = 0, 7
        prev, stack = {start: None}, [start]
        while stack:
            v = stack.pop()
            for w in adj[v]:
                if w not in prev:
                    prev[w] = v
                    stack.append(w)
        path, v = [], goal
        while prev[v] is not None:
            path.append((min(v, prev[v]), max(v, prev[v])))
            v = prev[v]
        ends = VGroup(Circle(0.22, color=RIM, stroke_width=5).move_to(dots[start]),
                      Circle(0.22, color=RIM, stroke_width=5).move_to(dots[goal]))
        self.wait(1.0)
        self.play(Create(ends), run_time=0.6)
        pl = VGroup(*[lines[e].copy().set_color(RIM).set_stroke(width=13) for e in path])
        self.play(LaggedStart(*[Create(l) for l in pl], lag_ratio=0.5), run_time=1.6)
        one = T("exactly one route between any two towns", 28, RIM).to_edge(DOWN, buff=0.6)
        self.play(FadeIn(one), run_time=0.6)
        self.done()
        self.play(FadeOut(VGroup(pl, ends, one, tdef)), run_time=0.5)

        # ---- cutting along the tree gives the net
        self.seg("st_cut")
        self.play(graph.animate.shift(3.3 * LEFT), tl.animate.set_color(CUT).shift(3.3 * LEFT), run_time=1.0)
        net = net_mob(tree, 4.0).shift(3.3 * RIGHT)
        arrow = Arrow(1.0 * LEFT, 1.0 * RIGHT, color=WHITE)
        self.play(GrowArrow(arrow), run_time=0.6)
        self.play(FadeIn(net), run_time=1.5)
        key = VGroup(
            VGroup(Line(ORIGIN, 0.6 * RIGHT, color=CUT, stroke_width=4), T("cut", 24, CUT)).arrange(RIGHT),
            VGroup(DashedLine(ORIGIN, 0.6 * RIGHT, color=WHITE, dash_length=0.08), T("uncut = hinge", 24)).arrange(RIGHT),
        ).arrange(RIGHT, buff=0.8).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(key), run_time=0.6)
        self.done()
        self.play(FadeOut(VGroup(graph, tl, net, arrow, key)), run_time=0.6)

        # ---- many trees
        self.seg("st_many")
        rng = random.Random(7)
        cells = VGroup()
        for k in range(8):
            tr = random_tree(rng)
            d2, l2 = cube_graph(schlegel, scale=0.33, ecol="#3a4250", width=2, dot=0.04)
            tlines = VGroup(*[l2[tuple(sorted(e))].copy().set_color(CUT).set_stroke(width=3) for e in tr])
            gph = VGroup(*l2.values(), tlines, d2)
            nm = net_mob(tr, 1.5, show_edges=False)
            cells.add(VGroup(gph, nm).arrange(DOWN, buff=0.25))
        cells.arrange_in_grid(2, 4, buff=(0.7, 0.45)).scale_to_fit_height(5.6).move_to(0.75 * DOWN)
        self.play(LaggedStart(*[FadeIn(c) for c in cells], lag_ratio=0.25), run_time=3.5)
        count = T("the cube has 384 spanning trees", 34, ACCENT).to_edge(UP, buff=0.35).shift(1.5 * RIGHT)
        self.play(Write(count), run_time=1.2)
        self.done()
        self.play(FadeOut(VGroup(cells, count)), run_time=0.6)


class S07_Generic(Scene2D):
    def construct(self):
        self.add(header("Generic spanning tree search"))
        self.seg("gs_algo")

        def box(s, col=WHITE, w=4.4):
            r = RoundedRectangle(width=w, height=0.9, corner_radius=0.15, color=col)
            return VGroup(r, T(s, 24, col))

        b1 = box("list every spanning tree")
        b2 = box("cut along it & unfold")
        b3 = box("any overlap?", ACCENT)
        yes = box("no overlap → YES", RIM)
        nxt = box("overlap → try next tree", NOTCH)
        none = box("ran out of trees → NO", CUT)
        b1.move_to([-3.6, 2.2, 0])
        b2.move_to([-3.6, 0.7, 0])
        b3.move_to([-3.6, -0.8, 0])
        yes.move_to([3.0, 0.7, 0])
        nxt.move_to([3.0, -1.4, 0])
        none.move_to([3.0, -2.9, 0])
        a1 = Arrow(b1.get_bottom(), b2.get_top(), buff=0.05)
        a2 = Arrow(b2.get_bottom(), b3.get_top(), buff=0.05)
        a3 = Arrow(b3.get_right(), yes.get_left(), buff=0.1, color=RIM)
        a4 = Arrow(b3.get_right(), nxt.get_left(), buff=0.1, color=NOTCH)
        a5 = CurvedArrow(nxt.get_top() + 1.6 * LEFT, b2.get_right() + 0.1 * RIGHT, angle=0.5, color=NOTCH)
        a6 = Arrow(nxt.get_bottom(), none.get_top(), buff=0.05, color=CUT)
        for grp in ((b1,), (a1, b2), (a2, b3), (a3, yes), (a4, nxt, a5), (a6, none)):
            self.play(*[FadeIn(g) for g in grp], run_time=0.7)
            self.wait(0.6)
        lock = T("≈ trying every combination on a lock", 28, SOFT).move_to([-3.6, -2.6, 0])
        self.play(FadeIn(lock), run_time=0.6)
        self.done()
        self.play(FadeOut(VGroup(b1, b2, b3, yes, nxt, none, a1, a2, a3, a4, a5, a6, lock)), run_time=0.6)

        self.seg("gs_growth")
        ns = list(range(3, 21))
        ax = Axes(x_range=[3, 21, 3], y_range=[0, 13, 2], x_length=7.2, y_length=4.6,
                  axis_config={"color": SOFT, "include_numbers": True, "font_size": 22},
                  tips=False).shift(2.2 * LEFT + 0.3 * DOWN)
        xl = T("sides of the prism's base (n)", 22, SOFT).next_to(ax, DOWN, buff=0.35)
        yl = T("digits in the number of trees", 22, SOFT).rotate(PI / 2).next_to(ax, LEFT, buff=0.35)
        self.play(Create(ax), FadeIn(xl), FadeIn(yl), run_time=1.2)
        pts = [ax.c2p(n, math.log10(G.prism_spanning_trees(n))) for n in ns]
        dots = VGroup(*[Dot(p, radius=0.06, color=ACCENT) for p in pts])
        curve = VMobject(color=ACCENT).set_points_smoothly(pts)
        self.play(Create(curve), LaggedStart(*[FadeIn(d) for d in dots], lag_ratio=0.1), run_time=3.0)
        approx = MathTex(r"\approx 3.7^{\,n}", color=ACCENT, font_size=48).next_to(pts[-4], UP + LEFT, buff=0.3)
        self.play(Write(approx), run_time=0.8)
        tbl = VGroup(*[
            VGroup(T(f"n = {n}", 26, SOFT), T(f"{G.prism_spanning_trees(n):,}", 26, WHITE)).arrange(RIGHT, buff=0.4)
            for n in (4, 10, 20)
        ]).arrange(DOWN, aligned_edge=RIGHT, buff=0.35).to_edge(RIGHT, buff=0.5).shift(0.6 * UP)
        for row in tbl:
            self.play(FadeIn(row, shift=0.2 * LEFT), run_time=0.6)
            self.wait(0.5)
        big = T("≈ 2.7 trillion", 30, CUT).next_to(tbl, DOWN, buff=0.4)
        self.play(FadeIn(big), Indicate(tbl[2], color=CUT), run_time=1.0)
        no = T("to say NO: check every one", 28, CUT).next_to(big, DOWN, buff=0.4)
        self.play(FadeIn(no), run_time=0.6)
        self.done()
        self.play(FadeOut(VGroup(ax, xl, yl, curve, dots, approx, tbl, big, no)), run_time=0.6)

        self.seg("gs_hard")
        l1 = T("General (dented) polytopes:", 34)
        l2 = T("NP-complete", 54, CUT)
        l3 = T("(Abel & Demaine, 2011)", 24, SOFT)
        l4 = T("⇒ look for a special case", 36, ACCENT)
        grp = VGroup(l1, l2, l3, l4).arrange(DOWN, buff=0.4)
        l4.shift(0.3 * DOWN)
        self.play(FadeIn(l1), run_time=0.6)
        self.play(Write(l2), FadeIn(l3), run_time=1.2)
        self.wait(3.0)
        self.play(FadeIn(l4, shift=0.2 * UP), run_time=0.8)
        self.done()
        self.play(FadeOut(grp), run_time=0.6)


class S08_Task(Scene2D):
    def construct(self):
        self.add(header("What we need"))
        self.seg("task_ask")
        t = T("Find a family of polytopes where…", 36).to_edge(UP, buff=1.0)
        c1 = VGroup(T("①", 40, RIM), T("some members unfold (YES), others can't (NO)", 30)).arrange(RIGHT, buff=0.4)
        c2 = VGroup(T("②", 40, ACCENT), T("an algorithm decides which,", 30)).arrange(RIGHT, buff=0.4)
        c2b = T("provably faster than trying all spanning trees", 30).next_to(c2, DOWN, aligned_edge=LEFT).shift(0.75 * RIGHT)
        grp = VGroup(c1, VGroup(c2, c2b)).arrange(DOWN, buff=0.7, aligned_edge=LEFT).next_to(t, DOWN, buff=0.8)
        self.play(FadeIn(t), run_time=0.8)
        self.wait(1.5)
        self.play(FadeIn(c1, shift=0.2 * RIGHT), run_time=0.8)
        self.wait(2.5)
        self.play(FadeIn(c2, shift=0.2 * RIGHT), FadeIn(c2b, shift=0.2 * RIGHT), run_time=0.8)
        self.done()
        self.play(FadeOut(VGroup(t, grp)), run_time=0.6)

        self.seg("task_convex")
        q = T("Why not convex polytopes?", 36).to_edge(UP, buff=1.0)
        self.play(FadeIn(q), run_time=0.6)
        nets = VGroup(net_mob(cross_tree(), 2.3, False),
                      net_mob(random_tree(random.Random(3)), 2.3, False),
                      net_mob(random_tree(random.Random(11)), 2.3, False)).arrange(RIGHT, buff=0.9).shift(0.2 * UP)
        ticks = VGroup(*[T("✓", 40, RIM).next_to(nm, DOWN, buff=0.2) for nm in nets])
        self.play(LaggedStart(*[FadeIn(nm) for nm in nets], lag_ratio=0.3), FadeIn(ticks), run_time=1.8)
        open_q = T("Every convex polytope ever tested CAN be edge-unfolded.", 28, RIM)
        open_q2 = T("Does one always exist?  OPEN (Dürer's problem, since the 1500s)", 28, ACCENT)
        VGroup(open_q, open_q2).arrange(DOWN, buff=0.3).to_edge(DOWN, buff=1.3)
        self.play(FadeIn(open_q), run_time=0.8)
        self.wait(2.0)
        self.play(FadeIn(open_q2), run_time=0.8)
        self.wait(3.0)
        need = T("⇒ for any NO answers we need dents", 32, NOTCH).to_edge(DOWN, buff=0.45)
        self.play(FadeIn(need, shift=0.2 * UP), run_time=0.8)
        self.done()
        self.play(FadeOut(VGroup(q, nets, ticks, open_q, open_q2, need)), run_time=0.6)


class S09_Prism(Scene3D):
    def construct(self):
        self.set_camera_orientation(phi=62 * DEGREES, theta=-70 * DEGREES, zoom=1.15)
        hdr = header("Our family: notched prisms")
        self.add_fixed_in_frame_mobjects(hdr)
        self.seg("fam_prism")
        poly = YES_POLY
        n = len(poly)
        h = ValueTracker(0.02)

        def make():
            P = G.prism(poly, h.get_value())
            cols = prism_colors(n)
            g = VGroup()
            order = [0] + list(range(2, n + 2)) + [1]
            for f in order:
                p = Polygon(*P.V[P.faces[f]], fill_color=cols[f], fill_opacity=0.92,
                            stroke_color=WHITE, stroke_width=1.2)
                p.set_shade_in_3d(True)
                g.add(p)
            return g

        cutter = Polygon(*[p3(p, 0) for p in poly], color=ACCENT, stroke_width=6)
        self.play(Create(cutter), run_time=1.5)
        cook = T("a cookie-cutter shape", 28, ACCENT).to_edge(DOWN)
        self.add_fixed_in_frame_mobjects(cook)
        self.play(FadeIn(cook), run_time=0.5)
        solid = always_redraw(make)
        self.add(solid)
        self.remove(cutter)
        self.play(h.animate.set_value(H), run_time=3.0)
        labels = VGroup(T("top lid", 28, LID), T("walls (rectangles, 90° to the lids)", 28, WALL),
                        T("bottom lid", 28, LID2)).arrange(DOWN, aligned_edge=LEFT).to_corner(UR, buff=0.6)
        self.add_fixed_in_frame_mobjects(labels)
        labels.set_opacity(0)
        self.play(FadeOut(cook), run_time=0.4)
        for lab in labels:
            self.play(lab.animate.set_opacity(1), run_time=0.6)
            self.wait(0.6)
        self.begin_ambient_camera_rotation(rate=0.15)
        self.done()
        self.stop_ambient_camera_rotation()
        self.play(FadeOut(solid), FadeOut(labels), run_time=0.6)


def notch_morph_poly(t, notched):
    """Decagon with side midpoints; midpoints of `notched` sides pushed in by fraction t."""
    pts = []
    m = M
    half = np.radians(OPENING) / 2
    for i in range(m):
        a = CONVEX10[i]
        b = CONVEX10[(i + 1) % m]
        mid = (a + b) / 2
        pts.append(a)
        if i in notched:
            side = np.linalg.norm(b - a)
            depth = (side / 2) / np.tan(half)
            pts.append(mid - t * depth * mid / np.linalg.norm(mid))
        else:
            pts.append(mid)
    return np.array(pts)


class S10_Notches(Scene2D):
    def construct(self):
        self.add(header("Our family: notched prisms"))
        self.seg("fam_notch")
        sc = 1.25
        notched = [1, 2, 4, 5, 6, 8, 9]
        prog = {i: ValueTracker(0) for i in notched}

        def shape():
            pts = []
            half = np.radians(OPENING) / 2
            for i in range(M):
                a, b = CONVEX10[i], CONVEX10[(i + 1) % M]
                mid = (a + b) / 2
                pts.append(a)
                if i in prog:
                    side = np.linalg.norm(b - a)
                    depth = (side / 2) / np.tan(half)
                    pts.append(mid - prog[i].get_value() * depth * mid / np.linalg.norm(mid))
            return poly2d(np.array(pts) * sc, fill_color=LID, fill_opacity=0.7, stroke_color=WHITE, stroke_width=3)

        cook = always_redraw(shape)
        lab = T("start convex…", 30, SOFT).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(cook), FadeIn(lab), run_time=1.0)
        self.wait(1.2)
        lab2 = T("…then cut narrow V-shaped notches into some sides", 30, NOTCH).to_edge(DOWN, buff=0.5)
        self.play(FadeOut(lab), FadeIn(lab2), run_time=0.5)
        self.play(LaggedStart(*[prog[i].animate.set_value(1) for i in notched], lag_ratio=0.35), run_time=4.0)
        cook.clear_updaters()
        # zoom into one notch: opening < 90, inside > 270
        i = 5
        pts = notch_morph_poly(1, set(notched)) * sc
        a, bottom, b = pts[2 * i], pts[2 * i + 1], pts[2 * i + 2]
        ang_open, _ = corner_arcs(bottom, a, b, 0.45, color=ACCENT, stroke_width=5)
        _, ang_in = corner_arcs(bottom, a, b, 0.3, color=RIM, stroke_width=5)
        lo = MathTex(r"<90^\circ", color=ACCENT, font_size=40)
        li = MathTex(r">270^\circ", color=RIM, font_size=40)
        out = bottom / np.linalg.norm(bottom)
        lo.move_to(p3(bottom + 1.0 * out))
        li.move_to(p3(bottom * 0.35))
        self.play(FadeOut(lab2), run_time=0.3)
        self.play(Create(ang_open), Write(lo), run_time=1.0)
        self.wait(1.4)
        self.play(Create(ang_in), Write(li), run_time=1.0)
        self.done()
        self.play(FadeOut(VGroup(ang_open, ang_in, lo, li)), run_time=0.4)

        self.seg("fam_kinds")
        self.play(cook.animate.shift(3.0 * LEFT), run_time=0.6)
        # drop the unused midpoints of un-notched sides so rim edges are single edges
        real, _ = G.notched_polygon(M, RADIUS, OPENING, set(notched), rotate_deg=-108)
        cols = edge_colors(real)
        el = edge_lines(real * sc, cols, 7).shift(3.0 * LEFT)
        self.play(Create(el), run_time=2.0)
        kinds = angle_kinds(real)
        rdots = VGroup(*[Dot(p3(real[j] * sc) + 3.0 * LEFT, radius=0.09, color=CUT) for j in range(len(real)) if kinds[j] == "reflex"])
        legend = VGroup(
            VGroup(Line(ORIGIN, 0.7 * RIGHT, color=RIM, stroke_width=7), T("rim edge (both corners convex)", 23, RIM)).arrange(RIGHT),
            VGroup(Line(ORIGIN, 0.7 * RIGHT, color=NOTCH, stroke_width=7), T("notch side (touches a sharp notch)", 23, NOTCH)).arrange(RIGHT),
            VGroup(Dot(color=CUT), T("sharp notch corner, > 270°", 23, CUT)).arrange(RIGHT),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.35).to_edge(RIGHT, buff=0.3).shift(0.6 * DOWN)
        self.play(FadeIn(legend[0]), *[Indicate(el[j], color=RIM) for j in range(len(real)) if cols[j] == RIM], run_time=1.5)
        self.wait(1.5)
        self.play(FadeIn(legend[1]), run_time=0.8)
        self.wait(1.0)
        self.play(FadeIn(legend[2]), FadeIn(rdots), run_time=0.8)
        nm = T("a notched prism = this shape, extruded", 28, SOFT).to_corner(UR, buff=0.5)
        self.play(FadeIn(nm), run_time=0.6)
        self.done()
        self.play(FadeOut(VGroup(cook, el, rdots, legend, nm)), run_time=0.6)


class S11_Theorem(Scene2D):
    def construct(self):
        self.add(header("The answer"))
        self.seg("thm_state")
        thm1 = T("A notched prism has a non-overlapping edge unfolding", 30)
        thm2 = VGroup(T("if and only if", 30, ACCENT), T("a piece of the original rim survives.", 30, RIM)).arrange(RIGHT, buff=0.25)
        thm = VGroup(thm1, thm2).arrange(DOWN, buff=0.2).to_edge(UP, buff=0.9)
        box = SurroundingRectangle(thm, color=ACCENT, buff=0.25, corner_radius=0.15)
        self.play(FadeIn(thm), Create(box), run_time=1.5)
        sc = 1.05
        saw = poly2d(SAW_POLY * sc, fill_color=LID, fill_opacity=0.65, stroke_width=0).shift(3.3 * LEFT + 0.9 * DOWN)
        yes = poly2d(YES_POLY * sc, fill_color=LID, fill_opacity=0.65, stroke_width=0).shift(3.3 * RIGHT + 0.9 * DOWN)
        se = edge_lines(SAW_POLY * sc, edge_colors(SAW_POLY), 5).shift(3.3 * LEFT + 0.9 * DOWN)
        ye = edge_lines(YES_POLY * sc, edge_colors(YES_POLY), 5).shift(3.3 * RIGHT + 0.9 * DOWN)
        self.wait(2.0)
        self.play(FadeIn(saw), Create(se), run_time=1.2)
        ln = T("every side notched → NO", 30, CUT).next_to(saw, DOWN, buff=0.35)
        self.play(FadeIn(ln), run_time=0.6)
        self.wait(2.2)
        self.play(FadeIn(yes), Create(ye), run_time=1.2)
        rim_i = G.rim_edges(YES_POLY)[0]
        ly = T("one rim edge left → YES", 30, RIM).next_to(yes, DOWN, buff=0.35)
        self.play(FadeIn(ly), Indicate(ye[rim_i], color=RIM, scale_factor=1.6), run_time=1.0)
        self.done()

        self.seg("thm_algo")
        self.play(FadeOut(VGroup(saw, se, ln)), VGroup(yes, ye, ly).animate.move_to(1.0 * DOWN), run_time=1.0)
        pts = YES_POLY * sc
        pts = pts + (ye.get_center()[:2] - (pts.max(0) + pts.min(0)) / 2)
        n = len(pts)
        kinds = angle_kinds(YES_POLY)
        walker = Dot(p3(pts[1]), radius=0.13, color=ACCENT, z_index=5)
        self.play(FadeIn(walker), run_time=0.3)
        order = list(range(1, n)) + [0]
        marks = VGroup()
        for j in order:
            nxt = (j + 1) % n
            self.play(walker.animate.move_to(p3(pts[nxt])), run_time=0.22)
            col = RIM if kinds[nxt] == "convex" else CUT
            mk = Dot(p3(pts[nxt]), radius=0.07, color=col, z_index=4)
            marks.add(mk)
            self.add(mk)
        found = SurroundingRectangle(ye[rim_i], color=RIM, buff=0.12)
        ft = T("both ends convex\n→ rim edge found", 26, RIM).next_to(yes, RIGHT, buff=0.6).shift(1.2 * DOWN)
        self.play(Create(found), FadeIn(ft), run_time=0.8)
        cost = MathTex(r"\text{time} = O(n)", font_size=48, color=ACCENT).to_edge(LEFT, buff=0.8).shift(DOWN)
        self.play(Write(cost), run_time=0.8)
        self.done()
        self.play(FadeOut(VGroup(thm, box, yes, ye, ly, walker, marks, found, ft, cost)), run_time=0.6)


class S12_YesFold(Scene3D):
    def construct(self):
        self.set_camera_orientation(phi=64 * DEGREES, theta=-62 * DEGREES, zoom=1.2)
        hdr = header("Proof, part 1: a rim edge survives ⇒ YES")
        self.add_fixed_in_frame_mobjects(hdr)
        poly = YES_POLY
        n = len(poly)
        rim = G.rim_edges(poly)[0]
        cutv = (rim + n // 2) % n
        P = G.prism(poly, H)
        U = G.strip_unfolding(P, n, rim, cutv)
        groups = {f: "band" for f in range(2, n + 2) if f != 2 + rim}
        groups[0] = "lid"
        groups[1] = "lid"
        fold = Folding(U, prism_colors(n), groups, opacity=0.93)

        self.seg("yes_cuts")
        self.play(FadeIn(fold), run_time=1.0)
        V = P.V
        vert = Line(V[cutv], V[n + cutv], color=CUT, stroke_width=8)
        top_cuts = VGroup(*[Line(V[n + i], V[n + (i + 1) % n], color=CUT, stroke_width=6) for i in range(n) if i != rim])
        bot_cuts = VGroup(*[Line(V[i], V[(i + 1) % n], color=CUT, stroke_width=6) for i in range(n) if i != rim])
        rim_lines = VGroup(Line(V[rim], V[rim + 1], color=RIM, stroke_width=10),
                           Line(V[n + rim], V[n + rim + 1], color=RIM, stroke_width=10))
        self.play(Create(rim_lines), run_time=0.8)
        self.wait(0.5)
        self.play(Create(vert), run_time=0.8)
        self.play(Create(top_cuts), run_time=1.6)
        self.play(Create(bot_cuts), run_time=1.6)
        lg = VGroup(T("red = cut", 26, CUT), T("green = rim edge (hinge)", 26, RIM)).arrange(DOWN, aligned_edge=LEFT).to_corner(UR, buff=0.5)
        self.add_fixed_in_frame_mobjects(lg)
        lg.set_opacity(0)
        self.play(lg.animate.set_opacity(1), run_time=0.5)
        self.done()

        self.seg("yes_unfold")
        self.play(FadeOut(VGroup(vert, top_cuts, bot_cuts, rim_lines)), run_time=0.5)
        self.move_camera(phi=78 * DEGREES, theta=-90 * DEGREES, zoom=0.62, run_time=1.2)
        self.play(fold.trackers["band"].animate.set_value(1), run_time=4.0)
        self.play(fold.trackers["lid"].animate.set_value(1), run_time=3.0)
        self.move_camera(phi=90 * DEGREES, theta=-90 * DEGREES, zoom=0.56, run_time=1.4)
        labs = VGroup(T("top lid", 28, LID).move_to([2.4, 2.2, 0]),
                      T("walls → one straight strip", 28, WALL).move_to([4.2, 1.0, 0]),
                      T("bottom lid", 28, LID).move_to([2.4, -1.9, 0]))
        self.add_fixed_in_frame_mobjects(labs)
        labs.set_opacity(0)
        self.play(FadeOut(lg), labs.animate.set_opacity(1), run_time=0.6)
        self.done()


def yes_net():
    n = len(YES_POLY)
    rim = G.rim_edges(YES_POLY)[0]
    U = G.strip_unfolding(G.prism(YES_POLY, H), n, rim, (rim + n // 2) % n)
    return U.flat_2d(), rim


class S13_YesWhy(Scene2D):
    def construct(self):
        self.add(header("Proof, part 1: a rim edge survives ⇒ YES"))
        flat, rim = yes_net()
        sc = 0.52
        allp = np.vstack(list(flat.values()))
        mid = (allp.min(0) + allp.max(0)) / 2
        n = len(YES_POLY)

        def tr(p):
            return (p - mid) * sc

        faces = VGroup()
        for f, pts in flat.items():
            col = LID if f == 1 else (LID2 if f == 0 else (WALL if f % 2 == 0 else WALL2))
            faces.add(poly2d(tr(pts), fill_color=col, fill_opacity=0.9, stroke_color=WHITE, stroke_width=1))
        self.add(faces)
        self.seg("yes_why")
        strip = VGroup(*[faces[k] for k, f in enumerate(flat) if f >= 2])
        top = [faces[k] for k, f in enumerate(flat) if f == 1][0]
        bot = [faces[k] for k, f in enumerate(flat) if f == 0][0]
        strip_box = SurroundingRectangle(strip, color=WALL, buff=0.03)
        self.play(Create(strip_box), run_time=0.8)
        st = T("the strip: just a rectangle", 26, WALL).next_to(strip_box, DOWN, buff=1.9).shift(3.5 * RIGHT)
        self.play(FadeIn(st), run_time=0.5)
        self.wait(1.2)
        y_top = tr(np.array([0, H]))[1]
        y_bot = tr(np.array([0, 0]))[1]
        line_t = DashedLine([-7.2, y_top, 0], [7.2, y_top, 0], color=RIM, stroke_width=4)
        line_b = DashedLine([-7.2, y_bot, 0], [7.2, y_bot, 0], color=RIM, stroke_width=4)
        self.play(Create(line_t), run_time=1.0)
        ruler = T("line through the rim edge", 24, RIM).next_to(line_t, UP, buff=0.08).to_edge(LEFT, buff=0.3)
        self.play(FadeIn(ruler), run_time=0.5)
        self.play(Indicate(top, color=LID, scale_factor=1.05), run_time=1.2)
        above = Rectangle(width=14.4, height=4.0 - y_top, stroke_width=0, fill_color=LID, fill_opacity=0.10)
        above.move_to([0, y_top + (4.0 - y_top) / 2, 0])
        self.play(FadeIn(above), run_time=0.8)
        txt = T("the whole lid sits on one side,\nlike a cookie against a ruler", 26, RIM).to_corner(UR, buff=0.35).shift(0.5 * DOWN)
        self.play(FadeIn(txt), run_time=0.6)
        self.wait(2.2)
        self.play(Create(line_b), run_time=0.8)
        below = Rectangle(width=14.4, height=4.0 + y_bot, stroke_width=0, fill_color=LID, fill_opacity=0.10)
        below.move_to([0, y_bot - (4.0 + y_bot) / 2, 0])
        self.play(FadeIn(below), Indicate(bot, color=LID2, scale_factor=1.05), run_time=1.2)
        ok = T("no overlaps ⇒ YES", 36, RIM).to_corner(DL, buff=0.5)
        self.play(Write(ok), run_time=1.0)
        self.done()
        self.play(FadeOut(Group(*[m for m in self.mobjects if m is not self.mobjects[0]])), run_time=0.6)


class S14_NoCorner(Scene2D):
    def construct(self):
        self.add(header("Proof, part 2: every side notched ⇒ NO"))
        self.seg("no_corner")
        sc = 1.5
        lid = poly2d(SAW_POLY * sc, fill_color=LID, fill_opacity=0.7, stroke_color=WHITE, stroke_width=2)
        self.play(FadeIn(lid), run_time=0.8)
        k = 1  # a notch bottom
        c = p3(SAW_POLY[k] * sc)
        ring = Circle(radius=0.35, color=ACCENT, stroke_width=5).move_to(c)
        self.play(Create(ring), run_time=0.6)
        self.play(lid.animate.shift(-c).scale(1.6, about_point=ORIGIN).shift(3.2 * LEFT + 0.6 * DOWN).set_fill(opacity=0.35),
                  FadeOut(ring), run_time=1.6)
        corner = 3.2 * LEFT + 0.6 * DOWN
        a_prev = (SAW_POLY[k - 1] - SAW_POLY[k])
        a_next = (SAW_POLY[k + 1] - SAW_POLY[k])
        _, arc = corner_arcs(corner[:2], corner[:2] + a_prev, corner[:2] + a_next, 0.7, color=RIM, stroke_width=6)
        lab = MathTex(r"\text{lid: } >270^\circ", font_size=40, color=RIM).move_to(corner + 1.6 * DOWN + 0.5 * LEFT)
        self.play(Create(arc), Write(lab), run_time=1.2)
        self.wait(0.8)
        # the two walls, schematic, stand on the lid edges
        walls = VGroup(T("+ wall: 90°", 34, WALL), T("+ wall: 90°", 34, WALL)).arrange(DOWN, aligned_edge=LEFT)
        walls.to_edge(RIGHT, buff=1.4).shift(1.4 * UP)
        for w in walls:
            w.add_background_rectangle(opacity=0.85, buff=0.1)
        self.play(FadeIn(walls[0]), run_time=0.6)
        self.play(FadeIn(walls[1]), run_time=0.6)
        total = MathTex(r"> 270^\circ + 90^\circ + 90^\circ = 450^\circ", font_size=44, color=ACCENT).next_to(walls, DOWN, buff=0.6).shift(0.4 * LEFT)
        total.add_background_rectangle(opacity=0.85, buff=0.1)
        self.play(Write(total), run_time=1.4)
        flat = MathTex(r"\text{flat paper: } 360^\circ", font_size=44, color=WHITE).next_to(total, DOWN, buff=0.5)
        self.wait(1.5)
        flat.add_background_rectangle(opacity=0.85, buff=0.1)
        self.play(Write(flat), run_time=1.0)
        self.done()
        self.play(FadeOut(VGroup(lid, arc, lab, walls, total, flat)), run_time=0.6)

        self.seg("no_fan")
        cen = 2.4 * LEFT + 0.2 * DOWN
        spec = [("wall", 90), ("lid", 300), ("wall", 90)]
        fan = build_fan(spec, cen, r=2.0)
        names = ["wall", "lid", "wall"]
        for p in fan:
            p.save_state()
        self.play(FadeIn(fan[0]), run_time=0.6)
        self.play(FadeIn(fan[1]), run_time=1.0)
        self.play(FadeIn(fan[2]), run_time=0.8)
        over = fan_overlap(fan)
        self.play(FadeIn(over), Flash(cen + 1.2 * RIGHT + 0.5 * UP, color=CUT), run_time=1.0)
        msg = T("glued faces fan out\naround one point;\nmore than 360° ⇒\nthey must overlap", 28, CUT).move_to([3.6, 1.2, 0])
        self.play(FadeIn(msg), run_time=0.8)
        collar = ParametricFunction(lambda t: np.array([4.1 + (0.9 + 0.12 * np.sin(9 * t)) * np.cos(t),
                                                        -1.9 + (0.9 + 0.12 * np.sin(9 * t)) * np.sin(t), 0]),
                                    t_range=[0, TAU], color=ACCENT, stroke_width=5)
        cl = T("ruffled collar", 24, ACCENT).next_to(collar, DOWN, buff=0.2)
        self.play(Create(collar), FadeIn(cl), run_time=1.4)
        self.done()
        self.play(FadeOut(VGroup(fan, over, msg, collar, cl)), run_time=0.6)


class S15_NoCases(Scene2D):
    def construct(self):
        self.add(header("Proof, part 2: every side notched ⇒ NO"))
        self.seg("no_cases")
        cases = [
            ("cut 1 edge", [[("wall", 90), ("lid", 300), ("wall", 90)]], False),
            ("cut vertical + 1 lid edge", [[("wall", 90)], [("lid", 300), ("wall", 90)]], False),
            ("cut both lid edges", [[("lid", 300)], [("wall", 90), ("wall", 90)]], True),
        ]
        cards = VGroup()
        for title, fans, ok in cases:
            row = VGroup()
            for spec in fans:
                fan = build_fan(spec, ORIGIN, r=0.75)
                ov = fan_overlap(fan)
                total = sum(d for _, d in spec)
                lab = T(f"{total}°", 22, CUT if total > 360 else RIM)
                grp = VGroup(fan, ov)
                lab.next_to(grp, DOWN, buff=0.15)
                row.add(VGroup(grp, lab))
            row.arrange(RIGHT, buff=0.35)
            head = T(title, 24, WHITE)
            verdict = T("✓ safe" if ok else "✗ overlap", 30, RIM if ok else CUT)
            card = VGroup(head, row, verdict).arrange(DOWN, buff=0.3)
            frame = SurroundingRectangle(card, color=RIM if ok else SOFT, buff=0.25, corner_radius=0.12)
            cards.add(VGroup(frame, card))
        cards.arrange(RIGHT, buff=0.4).scale_to_fit_width(13.2).shift(0.2 * DOWN)
        times = [5.0, 7.2, 4.0]
        for card, tm in zip(cards, times):
            self.play(FadeIn(card[0]), FadeIn(card[1][0]), FadeIn(card[1][1]), run_time=1.0)
            self.play(FadeIn(card[1][2], scale=1.3), run_time=0.5)
            self.wait(max(0.1, tm - 1.5))
        concl = T("⇒ at a sharp notch corner, BOTH lid edges must be cut", 30, ACCENT).to_edge(DOWN, buff=0.35)
        self.play(FadeIn(concl), run_time=0.8)
        self.done()
        self.play(FadeOut(VGroup(cards, concl)), run_time=0.6)


class S16_NoSaw(Scene2D):
    def construct(self):
        self.add(header("Proof, part 2: every side notched ⇒ NO"))
        self.seg("no_saw")
        sc = 1.25
        n = len(SAW_POLY)
        lid_poly = SPoly(SAW_POLY * sc)
        sh = 2.6 * LEFT
        outer = poly2d(np.array(lid_poly.buffer(0.22, join_style=1).exterior.coords)[:-1],
                       fill_color=WALL, fill_opacity=0.75, stroke_width=0).shift(sh)
        lid = poly2d(SAW_POLY * sc, fill_color=LID, fill_opacity=1.0, stroke_width=0).shift(sh)
        edges = edge_lines(SAW_POLY * sc, [WHITE] * n, 4).shift(sh)
        wl = T("walls", 26, WALL).next_to(outer, LEFT, buff=0.2)
        ll = T("lid", 26, WHITE).move_to(sh)
        self.play(FadeIn(outer), FadeIn(lid), Create(edges), FadeIn(wl), FadeIn(ll), run_time=1.2)
        kinds = angle_kinds(SAW_POLY)
        for j in range(n):
            if kinds[j] != "reflex":
                continue
            d = Dot(p3(SAW_POLY[j] * sc) + sh, radius=0.1, color=ACCENT, z_index=3)
            self.play(FadeIn(d, scale=2), edges[j - 1].animate.set_color(CUT), edges[j].animate.set_color(CUT),
                      run_time=0.42)
            self.add(d)
        allcut = T("every lid edge is cut", 30, CUT).move_to([3.3, 2.6, 0])
        self.play(FadeIn(allcut), run_time=0.6)
        self.wait(0.8)
        self.play(VGroup(lid, edges, ll).animate.shift(5.6 * RIGHT + 0.2 * UP).rotate(0.35), run_time=1.8)
        falls = T("the lid is attached to nothing\n→ not one piece", 28, CUT).to_corner(DR, buff=0.4)
        self.play(FadeIn(falls), run_time=0.6)
        no = T("NO unfolding exists", 40, CUT).to_corner(DL, buff=0.4)
        self.play(Write(no), run_time=1.0)
        self.done()
        self.play(FadeOut(Group(*[m for m in self.mobjects if m is not self.mobjects[0]])), run_time=0.5)

        self.seg("no_all")
        big = T(f"{G.prism_spanning_trees(20):,} spanning trees", 40, WHITE)
        self.play(FadeIn(big), run_time=0.8)
        strike = Line(big.get_left(), big.get_right(), color=CUT, stroke_width=8)
        self.play(Create(strike), run_time=0.8)
        sub = T("ruled out at once, without checking any", 30, ACCENT).next_to(big, DOWN, buff=0.5)
        self.play(FadeIn(sub), run_time=0.6)
        self.done()
        self.play(FadeOut(VGroup(big, strike, sub)), run_time=0.5)

        self.seg("no_narrow")
        t1 = T("Why the notches must be narrow", 34, ACCENT).to_edge(UP, buff=0.9)
        self.play(FadeIn(t1), run_time=0.6)
        sharp = build_fan([("lid", 300), ("wall", 90)], 3.6 * LEFT + 0.5 * DOWN, r=1.4)
        wide = build_fan([("lid", 240), ("wall", 90)], 3.0 * RIGHT + 0.5 * DOWN, r=1.4)
        so = fan_overlap(sharp)
        lab_s = T("narrow notch: 300° + 90° = 390°  ✗", 24, CUT).move_to([-3.5, -2.55, 0])
        lab_w = T("wide notch: 240° + 90° = 330°  fits", 24, RIM).move_to([3.4, -2.55, 0])
        self.play(FadeIn(sharp), FadeIn(so), FadeIn(lab_s), run_time=1.0)
        self.wait(3.0)
        self.play(FadeIn(wide), FadeIn(lab_w), run_time=1.0)
        brk = T("argument breaks; answer depends on fine details", 28, SOFT).to_edge(DOWN, buff=0.3)
        self.wait(2.0)
        self.play(FadeIn(brk), run_time=0.6)
        self.done()
        self.play(FadeOut(VGroup(t1, sharp, so, wide, lab_s, lab_w, brk)), run_time=0.5)


class S17_Fast(Scene2D):
    def construct(self):
        self.add(header("Why it's provably faster"))
        self.seg("fast_split")
        q = T("each edge of a notched prism's polygon is…", 30).to_edge(UP, buff=1.0)
        left = VGroup(T("a rim edge", 32, RIM), T("⇒ strip unfolding ⇒ YES", 28, RIM)).arrange(DOWN)
        right = VGroup(T("a notch side", 32, NOTCH), T("touches a > 270° corner", 28, NOTCH)).arrange(DOWN)
        VGroup(left, right).arrange(RIGHT, buff=2.0).shift(0.4 * UP)
        self.play(FadeIn(q), run_time=0.6)
        self.play(FadeIn(left), FadeIn(right), run_time=0.8)
        d1 = T("some rim edge exists  →  YES", 30, RIM)
        d2 = T("no rim edge at all  →  NO", 30, CUT)
        dec = VGroup(d1, d2).arrange(DOWN, buff=0.3).shift(1.7 * DOWN)
        self.wait(1.5)
        self.play(FadeIn(d1, shift=0.2 * UP), run_time=0.7)
        self.wait(0.8)
        self.play(FadeIn(d2, shift=0.2 * UP), run_time=0.7)
        exact = SurroundingRectangle(dec, color=ACCENT, buff=0.2)
        self.play(Create(exact), run_time=0.7)
        self.done()
        self.play(FadeOut(VGroup(q, left, right, dec, exact)), run_time=0.5)

        self.seg("fast_compare")
        ax = Axes(x_range=[4, 40, 6], y_range=[0, 32, 5], x_length=8.5, y_length=4.8,
                  axis_config={"color": SOFT, "include_numbers": True, "font_size": 22}, tips=False).shift(0.6 * LEFT + 0.4 * DOWN)
        xl = T("n (sides of the polygon)", 22, SOFT).next_to(ax, DOWN, buff=0.3)
        yl = T("digits in the step count", 22, SOFT).rotate(PI / 2).next_to(ax, LEFT, buff=0.3)
        self.play(Create(ax), FadeIn(xl), FadeIn(yl), run_time=1.0)
        ns = np.arange(4, 41, 1)
        ex = VMobject(color=CUT, stroke_width=5).set_points_as_corners(
            [ax.c2p(k, math.log10(G.prism_spanning_trees(int(k)))) for k in ns])
        lin = VMobject(color=RIM, stroke_width=5).set_points_as_corners([ax.c2p(k, np.log10(k)) for k in ns])
        le = T("brute force: every spanning tree (≈ 3.7ⁿ)", 24, CUT).move_to(ax.c2p(17, 27))
        ll = T("our check: one walk around (n)", 24, RIM).next_to(ax.c2p(26, 2), UP, buff=0.2)
        self.play(Create(ex), FadeIn(le), run_time=1.8)
        self.play(Create(lin), FadeIn(ll), run_time=1.4)
        tag = T("linear vs exponential", 34, ACCENT).to_corner(UR, buff=0.6)
        self.play(Write(tag), run_time=1.0)
        self.done()
        self.play(FadeOut(VGroup(ax, xl, yl, ex, lin, le, ll, tag)), run_time=0.5)


class S18_Recap(Scene2D):
    def construct(self):
        self.add(header("The solution in one breath"))
        self.seg("recap")
        items = [
            ("Family:", "prisms over convex polygons with narrow (< 90°) V-notches", WHITE),
            ("Rim edge survives:", "unroll walls into a strip, swing lids off it → YES", RIM),
            ("Every side notched:", "> 360° at each notch corner unless both lid edges", CUT),
            (None, "are cut → the lid is cut off entirely → NO", CUT),
            ("Speed:", "look for a rim edge in O(n), vs. exponentially many trees", ACCENT),
        ]
        rows = VGroup()
        for a, b, col in items:
            rows.add(VGroup(T(b, 26, WHITE)) if a is None else VGroup(T(a, 28, col), T(b, 26, WHITE)).arrange(RIGHT, buff=0.3))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.42).to_edge(LEFT, buff=0.6).shift(1.2 * UP)
        rows[3].shift(RIGHT * (rows[2][1].get_left()[0] - rows[3][0].get_left()[0]))
        flat, rim = yes_net()
        allp = np.vstack(list(flat.values()))
        mid = (allp.min(0) + allp.max(0)) / 2
        net = VGroup(*[poly2d((p - mid) * 0.2, fill_color=LID if f < 2 else WALL, fill_opacity=0.85,
                              stroke_color=WHITE, stroke_width=0.6) for f, p in flat.items()])
        net.to_edge(DOWN, buff=0.5).shift(3.3 * LEFT)
        saw = poly2d(SAW_POLY * 0.55, fill_color=LID, fill_opacity=0.8, stroke_color=CUT, stroke_width=3)
        saw.to_edge(DOWN, buff=0.45).shift(3.0 * RIGHT)
        times = [4.0, 6.5, 6.0, 3.5, 5.5]
        for r, tm, extra in zip(rows, times, [None, net, saw, None, None]):
            anims = [FadeIn(r, shift=0.15 * RIGHT)]
            if extra is not None:
                anims.append(FadeIn(extra))
            self.play(*anims, run_time=0.8)
            self.wait(tm)
        self.done()

        self.seg("outro")
        self.play(FadeOut(VGroup(rows, net, saw)), run_time=0.6)
        thanks = T("Thanks for watching", 44, ACCENT)
        self.play(FadeIn(thanks), run_time=0.5)
        self.done(pad=1.2)


SCENES = [
    "S01_Intro", "S02_Polytope", "S03_Convex", "S04_Unfold", "S05_Overlap", "S06_Graph",
    "S07_Generic", "S08_Task", "S09_Prism", "S10_Notches", "S11_Theorem", "S12_YesFold",
    "S13_YesWhy", "S14_NoCorner", "S15_NoCases", "S16_NoSaw", "S17_Fast", "S18_Recap",
]
