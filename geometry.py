"""Geometry helpers: notched polygons, prisms, and hinge-by-hinge unfolding."""
from collections import deque
from math import comb, sqrt

import numpy as np


# ------------------------------------------------------------------ polygons
def notched_polygon(m=10, radius=2.0, opening_deg=60.0, notched=None, rotate_deg=90.0):
    """Regular m-gon with a V notch cut into each side listed in `notched`.

    Each notch spans its whole side and opens by `opening_deg` at its bottom.
    Returns (vertices Nx2 CCW, kinds) where kinds[i] is 'tip', 'corner'
    (an original corner of the convex polygon) or 'notch' (reflex bottom).
    """
    if notched is None:
        notched = set(range(m))
    half = np.radians(opening_deg) / 2
    angles = np.radians(rotate_deg) + 2 * np.pi * np.arange(m) / m
    corners = radius * np.column_stack([np.cos(angles), np.sin(angles)])
    verts, kinds = [], []
    for i in range(m):
        a, b = corners[i], corners[(i + 1) % m]
        verts.append(a)
        kinds.append("corner")
        if i in notched:
            mid = (a + b) / 2
            side = np.linalg.norm(b - a)
            inward = -mid / np.linalg.norm(mid)
            depth = (side / 2) / np.tan(half)
            verts.append(mid + depth * inward)
            kinds.append("notch")
    return np.array(verts), kinds


def interior_angles(poly):
    """Interior angle (radians) at each vertex of a CCW polygon."""
    n = len(poly)
    out = []
    for i in range(n):
        p, c, q = poly[i - 1], poly[i], poly[(i + 1) % n]
        a1 = np.arctan2(*(p - c)[::-1])
        a2 = np.arctan2(*(q - c)[::-1])
        ang = (a1 - a2) % (2 * np.pi)  # CCW polygon: sweep from next to prev
        out.append(ang)
    return np.array(out)


def rim_edges(poly):
    """Indices i of edges (i, i+1) whose two endpoints are both convex."""
    ang = interior_angles(poly)
    n = len(poly)
    return [i for i in range(n) if ang[i] < np.pi and ang[(i + 1) % n] < np.pi]


# ----------------------------------------------------------------- polyhedra
class Polyhedron:
    def __init__(self, verts, faces):
        self.V = np.asarray(verts, dtype=float)
        self.faces = [list(f) for f in faces]  # CCW seen from outside
        self.edge_faces = {}
        for fi, f in enumerate(self.faces):
            for k in range(len(f)):
                e = frozenset((f[k], f[(k + 1) % len(f)]))
                self.edge_faces.setdefault(e, []).append(fi)
        self.edges = list(self.edge_faces)

    def normal(self, fi):
        p = self.V[self.faces[fi]]
        n = np.zeros(3)
        for k in range(len(p)):
            n += np.cross(p[k], p[(k + 1) % len(p)])
        return n / np.linalg.norm(n)


def prism(poly2d, height=1.0):
    """Right prism over a CCW polygon. Faces: 0 bottom, 1 top, 2+i wall on edge i."""
    n = len(poly2d)
    bot = [np.array([x, y, 0.0]) for x, y in poly2d]
    top = [np.array([x, y, height]) for x, y in poly2d]
    verts = bot + top
    faces = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    return Polyhedron(verts, faces)


def cube(s=2.0):
    h = s / 2
    V = [(x, y, z) for z in (-h, h) for y in (-h, h) for x in (-h, h)]
    # index = x + 2y + 4z  (0/1 for -h/h)
    faces = [
        [0, 2, 3, 1],  # bottom z-
        [4, 5, 7, 6],  # top z+
        [0, 1, 5, 4],  # front y-
        [2, 6, 7, 3],  # back y+
        [0, 4, 6, 2],  # left x-
        [1, 3, 7, 5],  # right x+
    ]
    return Polyhedron(V, faces)


def square_pyramid(s=2.0, h=1.6):
    a = s / 2
    V = [(-a, -a, 0), (a, -a, 0), (a, a, 0), (-a, a, 0), (0, 0, h)]
    faces = [[3, 2, 1, 0], [0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]
    return Polyhedron(V, faces)


# ----------------------------------------------------------------- unfolding
def rotation(axis, angle):
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    c, s = np.cos(angle), np.sin(angle)
    C = 1 - c
    return np.array([
        [c + x * x * C, x * y * C - z * s, x * z * C + y * s],
        [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
        [z * x * C - y * s, z * y * C + x * s, c + z * z * C],
    ])


class Unfolding:
    """Faces hinged along uncut edges, rooted at one face.

    For each face we store its parent, the hinge (a, b) in the folded
    position, and the angle that makes it coplanar with its parent.
    """

    def __init__(self, P, cut_edges, root=0):
        self.P = P
        cut = {frozenset(e) for e in cut_edges}
        self.root = root
        self.parent = {root: None}
        self.hinge = {}
        self.angle = {}
        self.order = [root]
        q = deque([root])
        while q:
            f = q.popleft()
            fv = P.faces[f]
            for k in range(len(fv)):
                e = frozenset((fv[k], fv[(k + 1) % len(fv)]))
                if e in cut:
                    continue
                for g in P.edge_faces[e]:
                    if g != f and g not in self.parent:
                        self.parent[g] = f
                        a, b = (P.V[v] for v in e)
                        u = (b - a) / np.linalg.norm(b - a)
                        nc, npar = P.normal(g), P.normal(f)
                        self.hinge[g] = (a, u)
                        self.angle[g] = np.arctan2(np.dot(np.cross(nc, npar), u), np.dot(nc, npar))
                        self.order.append(g)
                        q.append(g)
        if len(self.order) != len(P.faces):
            raise ValueError("uncut edges do not connect all faces")

    def face_points(self, f, t):
        """3D points of face f when each face g has opened by fraction t(g)."""
        pts = self.P.V[self.P.faces[f]].copy()
        g = f
        while self.parent[g] is not None:
            a, u = self.hinge[g]
            R = rotation(u, self.angle[g] * t(g))
            pts = (pts - a) @ R.T + a
            g = self.parent[g]
        return pts

    def flat_2d(self):
        """Fully unfolded faces, as 2D polygons in the root face's plane."""
        P = self.P
        r = P.V[P.faces[self.root]]
        n = P.normal(self.root)
        ex = (r[1] - r[0]) / np.linalg.norm(r[1] - r[0])
        ey = np.cross(n, ex)
        out = {}
        for f in self.order:
            p = self.face_points(f, lambda g: 1.0) - r[0]
            out[f] = np.column_stack([p @ ex, p @ ey])
        return out


def strip_unfolding(P, n, rim, cut_vertex):
    """Cut tree for the prism 'strip' net: hinge both lids on wall `rim`."""
    cuts = []
    for i in range(n):
        if i != rim:
            cuts.append((i, (i + 1) % n))
            cuts.append((n + i, n + (i + 1) % n))
    cuts.append((cut_vertex, n + cut_vertex))
    return Unfolding(P, cuts, root=2 + rim)


# ------------------------------------------------------------------- counting
def prism_spanning_trees(n):
    """Exact number of spanning trees of the n-sided prism graph C_n x K_2."""
    # tau = (n/2) * ((2+sqrt3)^n + (2-sqrt3)^n - 2); use the integer recurrence
    # L_k = 4 L_{k-1} - L_{k-2}, L_0 = 2, L_1 = 4  for (2+s)^k + (2-s)^k.
    a, b = 2, 4
    for _ in range(n - 1):
        a, b = b, 4 * b - a
    L = b if n >= 1 else a
    return n * (L - 2) // 2


if __name__ == "__main__":
    print("cube-like prism n=4:", prism_spanning_trees(4))
    for n in (6, 10, 20, 40):
        print(n, f"{prism_spanning_trees(n):,}")
    saw, kinds = notched_polygon(notched=None)
    yes, _ = notched_polygon(notched=set(range(1, 10)))
    print("saw angles", np.degrees(interior_angles(saw)).round(1)[:4], "rim:", rim_edges(saw))
    print("yes angles", np.degrees(interior_angles(yes)).round(1)[:4], "rim:", rim_edges(yes))
