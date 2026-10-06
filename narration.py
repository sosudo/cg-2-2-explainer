"""Narration for the explainer, split into short segments.

Each scene in scenes.py plays its segments in order; make_audio.py turns every
segment into a WAV with Kokoro-82M (voice af_heart) and records its duration so
the animations can be timed to the voice.
"""

SEGMENTS = {
    # ---------------------------------------------------------------- intro
    "intro_box": (
        "Imagine a cereal box. If you slice along some of its edges, you can "
        "flatten the whole box into one piece of cardboard. That flat piece is "
        "called an unfolding."
    ),
    "intro_goal": (
        "In this video we'll solve a puzzle about unfoldings. We need a family "
        "of shapes where the answer can be yes or no, and where we can decide "
        "which one, provably faster than brute force. By the end, you'll be "
        "able to explain the whole solution in a few sentences."
    ),
    # ---------------------------------------------------------- definitions
    "def_polytope": (
        "First, some vocabulary. A polytope, for us, is a solid whose surface "
        "is made of flat polygons, called faces. Faces meet along straight "
        "edges, and edges meet at corners, called vertices. A cube, a pyramid, "
        "and a prism are all polytopes."
    ),
    "def_convex": (
        "A polytope is convex if it has no dents. Think of shrink wrap. On a "
        "convex shape the wrap hugs every face. On a dented shape, the wrap "
        "bridges straight over the dent."
    ),
    "def_unfold": (
        "An edge cut unfolding means you may only cut along edges, never "
        "through the middle of a face. After cutting, the surface must open "
        "up into one single, connected, flat piece, like a sewing pattern."
    ),
    "def_overlap": (
        "The unfolding is non-overlapping if no two faces land on top of each "
        "other. Here is one that fails: the red region is covered twice, so "
        "you could never cut this pattern out of a single sheet of paper."
    ),
    "def_problem": (
        "So here is the problem. You are handed a polytope. Is there some "
        "choice of edges to cut, so that it unfolds into one flat piece with "
        "no overlaps? The answer is simply yes, or no."
    ),
    # ------------------------------------------------------- spanning trees
    "st_graph": (
        "Which sets of edges can we cut? Draw the polytope's skeleton: a dot "
        "for every vertex and a line for every edge. Mathematicians call this "
        "a graph. Think of it as a map of towns and roads."
    ),
    "st_rules": (
        "The cuts have to reach every corner. A party hat won't lie flat "
        "unless you slit it all the way to the tip, and every corner of a "
        "polytope is a little party hat. The cuts also can't form a loop, "
        "because a loop slices a piece clean off. And the standard fact from "
        "class is that, put together, the cut edges always form a spanning "
        "tree."
    ),
    "st_define": (
        "A spanning tree is a set of edges that connects every vertex, with "
        "no loops. Picture the cheapest road network that links every town: "
        "you can get anywhere, but there are no redundant roads, so there is "
        "exactly one route between any two towns."
    ),
    "st_cut": (
        "Cut along a spanning tree, and the faces stay hinged together along "
        "every uncut edge. Open the hinges, and out comes the unfolding."
    ),
    "st_many": (
        "Different spanning trees give different unfoldings. The cube alone "
        "has three hundred eighty four spanning trees, so three hundred eighty "
        "four ways to cut the box."
    ),
    # ------------------------------------------------------- generic search
    "gs_algo": (
        "That suggests the obvious algorithm, which we'll call generic "
        "spanning tree search. List every spanning tree. For each one, cut, "
        "unfold, and check for overlaps. If any tree works, say yes. If none "
        "work, say no. It's like opening a combination lock by trying every "
        "combination."
    ),
    "gs_growth": (
        "The trouble is how fast the number of trees grows. For a prism whose "
        "base has n sides, it grows roughly like three point seven to the "
        "power n. A twenty sided prism already has about two point seven "
        "trillion spanning trees. And to answer no, brute force has to check "
        "every single one."
    ),
    "gs_hard": (
        "Worse, for general dented polytopes this problem is known to be N P "
        "complete, so we shouldn't hope for a fast algorithm that works on "
        "every shape. That is why the question asks for a special case."
    ),
    # ------------------------------------------------------------ the task
    "task_ask": (
        "Here is exactly what we need. A family of shapes where, one: some "
        "members can be unfolded, and some can't. And two: some algorithm "
        "decides which, provably faster than trying all the spanning trees."
    ),
    "task_convex": (
        "Why not just use convex shapes? Because no one has ever found a "
        "convex polytope that can't be edge unfolded. That's a famous open "
        "problem, going back to the nets drawn by Albrecht Durer in the fifteen "
        "hundreds. So to get any no answers at all, our shapes need dents."
    ),
    # -------------------------------------------------------------- family
    "fam_prism": (
        "Our family is built from prisms. Take a flat polygon, like a cookie "
        "cutter, and push it straight up, the way dough comes out of a "
        "Play-Doh extruder. You get a top lid and a bottom lid, joined by a "
        "ring of rectangular walls standing at right angles."
    ),
    "fam_notch": (
        "Now choose the polygon in a special way. Start with a convex "
        "polygon, and cut narrow V shaped notches into some of its sides. "
        "Narrow means each V opens by less than ninety degrees. So the "
        "inside corner at the bottom of every notch is more than two hundred "
        "seventy degrees."
    ),
    "fam_kinds": (
        "Call the extruded shape a notched prism. Every edge of its polygon "
        "is one of two kinds. Either it's a surviving piece of the original "
        "rim, shown in green, or it's the side of a notch, shown in orange, "
        "and it touches a sharp notch corner."
    ),
    # ------------------------------------------------------------- theorem
    "thm_state": (
        "Here is the entire answer. A notched prism has a non-overlapping "
        "edge unfolding if and only if at least one piece of the original rim "
        "survives. If every side got notched, like this saw blade, it's "
        "impossible. Leave just one side un-notched, and it becomes possible."
    ),
    "thm_algo": (
        "So the algorithm is a single walk around the polygon, looking for an "
        "edge whose two endpoints are both convex corners. That takes time "
        "proportional to n. No trees required. Now let's prove both "
        "directions."
    ),
    # ---------------------------------------------------------- yes proof
    "yes_cuts": (
        "First, yes. Suppose some rim edge survives. Here are the cuts: slice "
        "down one vertical edge, then slice all the way around the top lid and "
        "the bottom lid, except along that rim edge."
    ),
    "yes_unfold": (
        "Now unfold. The walls unroll into one long, straight strip, like "
        "peeling the label off a soup can. Then the top lid swings up, and the "
        "bottom lid swings down, both hinged on the rim edge."
    ),
    "yes_why": (
        "Why can't anything overlap? The strip is just a rectangle. And "
        "because our hinge is on the outer rim, the whole lid sits on one side "
        "of the line through it, like a cookie resting against a ruler. So "
        "the top lid stays above the strip, and the bottom lid stays below "
        "it. Nothing collides. Whenever a rim edge survives, the answer is yes."
    ),
    # ----------------------------------------------------------- no proof
    "no_corner": (
        "Now the no direction, which is the clever part. Zoom in on the "
        "bottom of one notch, on the top lid. Three faces meet at this "
        "corner. The lid brings more than two hundred seventy degrees, and "
        "each wall brings ninety. That's more than four hundred fifty degrees "
        "of paper around a single point. A flat sheet only has three hundred "
        "sixty."
    ),
    "no_fan": (
        "Faces around a corner that we don't cut apart stay glued together, "
        "so in the unfolding they fan out around one point. And a fan of more "
        "than three hundred sixty degrees must overlap itself, like a ruffled "
        "collar that refuses to lie flat."
    ),
    "no_cases": (
        "So which edges can we cut at this corner? Cut just one edge, and all "
        "four hundred fifty degrees stay in one fan: overlap. Cut the vertical "
        "edge and one lid edge, and the lid stays glued to a wall: two "
        "seventy plus ninety is over three sixty: overlap again. The only "
        "safe choices cut both lid edges at this corner."
    ),
    "no_saw": (
        "Now take the saw blade, where every side was notched. Every edge of "
        "its lid touches some notch corner, so every edge of the lid must be "
        "cut. But then the lid isn't attached to anything. It falls off, and "
        "the unfolding is not one piece. So no unfolding can possibly work."
    ),
    "no_all": (
        "Notice that this argument rules out all two point seven trillion "
        "spanning trees at once, without looking at a single one."
    ),
    "no_narrow": (
        "It also shows why the notches must be narrow. With a wide notch, say "
        "two hundred forty degrees inside, the lid plus a wall is only three "
        "hundred thirty degrees. The argument breaks, and the answer depends "
        "on fine details again."
    ),
    # -------------------------------------------------------------- faster
    "fast_split": (
        "Putting it together: in a notched prism, every edge is either a rim "
        "edge or touches a sharp notch corner. Rim edge present: yes. No rim "
        "edge: no. So looking for a rim edge decides the question exactly."
    ),
    "fast_compare": (
        "That check takes linear time. Generic search, on the saw blade, must "
        "examine every spanning tree before it can say no, and there are "
        "exponentially many. Linear against exponential: provably faster."
    ),
    # --------------------------------------------------------------- recap
    "recap": (
        "So here's the solution in one breath. Take prisms made from convex "
        "polygons with narrow notches cut in. If any piece of the original "
        "rim survives, unroll the walls into a strip and swing the lids off "
        "that rim edge: yes. If every side is notched, each notch corner has "
        "over three hundred sixty degrees of paper unless both lid edges there "
        "are cut, so the lid gets cut off completely: no. Checking for a rim "
        "edge takes linear time, while brute force over spanning trees takes "
        "exponential time."
    ),
    "outro": "Thanks for watching.",
}
