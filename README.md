# Unfolding notched prisms: an explainer

**Watch:** [`explainer.mp4`](explainer.mp4) (8m50s, 1080p, voice: Kokoro-82M `af_heart`)

## The problem

Find a special case of the problem "does this 3D polytope have a non-overlapping
edge-cut unfolding?" such that (1) the answer can be yes or no, and (2) some
algorithm is provably faster than generic spanning tree search, which tries every
spanning tree of the polytope's vertex/edge graph as a cut set.

## The solution

**Family.** Take a convex polygon and cut narrow V-shaped notches into some of its
sides. Each V opens by less than 90°, so the inside angle at the bottom of each notch
is more than 270°. Extrude the polygon straight up to get a right prism (a *notched
prism*). Each polygon edge is one of two kinds:
* a **rim edge**: a surviving piece of the original boundary. Both of its endpoints are
  convex, and it lies on the convex hull.
* a **notch side**, which touches a notch bottom with an angle above 270°.

**Theorem.** A notched prism has a non-overlapping edge unfolding if and only if
it has a rim edge.

*Yes, if a rim edge g exists.* Cut one vertical edge, and cut every top and bottom
edge except the two copies of g. The walls unroll into one straight strip, and the
two lids hinge off the strip along g. Because g is on the convex hull, each lid lies
entirely on its own side of the line through g. So the top lid sits above the strip
and the bottom lid sits below it, and nothing overlaps.

*No, if every side is notched.* Look at a notch bottom v on the top lid. Three faces
meet there: the lid (more than 270°) and two walls (90° each). Faces around v that are
not cut apart stay glued, so in the plane they fan out around one copy of v, and a
fan of more than 360° overlaps itself. Here are the possible cuts at v:
* Cut one edge: one fan of more than 450°, so it overlaps.
* Cut the vertical edge and one lid edge: the lid and one wall form a fan of more
  than 360°, so it overlaps.
* Cut both lid edges: fans of more than 270° and of 180°. This is the only safe choice.

So both lid edges at every notch bottom must be cut. On a fully notched polygon, every
lid edge touches a notch bottom, so every lid edge is cut. Then the lid is attached to
nothing and the unfolding is not one piece. This argument only needs the unfolding to
be one connected piece, so it rules out every spanning tree at once.

**Algorithm.** Walk around the polygon and look for an edge whose two endpoints are
both convex. That takes O(n) time. On a fully notched input, generic search has to
reject every spanning tree of the prism graph before it can answer no. That graph has
τ(n) = (n/2)((2+√3)^n + (2−√3)^n − 2) ≈ 3.7^n spanning trees, for example
2,747,583,822,720 when n = 20. Linear time against exponential time is provably
faster.

The restriction to narrow notches matters. With a 240° notch, the lid plus one wall
is only 330°, the local argument fails, and the answer depends on finer geometry.

## Rebuilding

```bash
pip install manim kokoro-onnx soundfile shapely      # plus ffmpeg, LaTeX, pango
# Kokoro-82M ONNX weights: kokoro-v1.0.onnx + voices-v1.0.bin from
# https://github.com/thewh1teagle/kokoro-onnx/releases (model-files-v1.0), in $KOKORO_DIR
python make_audio.py      # narration.py -> audio/*.wav + audio/durations.json
./build.sh                # renders scenes.py and stitches explainer.mp4
```

* `narration.py`: the voice-over script, one entry per segment
* `geometry.py`: notched polygons, prisms, hinge unfolding, spanning-tree counts
* `scenes.py`: the manim scenes, each timed to its narration segment
