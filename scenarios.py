"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # Criterion 3 — state. A different matching query from criterion 1,
        # so the id check isn't only ever run on one item. What's checked is
        # session["selected_item"], search_results[0] and session["tool_inputs"].
        "name": "selected item reaches both tools",
        "query": "denim jacket under $50",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 4 — the fit card. The SAME query five times, cache off, so
        # the five cards can be compared with each other.
        "name": "fit card is postable",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 4,
    },
    # Criterion 5 — the search filters. Five different queries, one try each:
    # the search is deterministic, so the five queries are the five tries.
    {"name": "filters: price", "query": "vintage graphic tee under $30",
     "wardrobe": "example", "criterion": 5, "tries": 1},
    {"name": "filters: size M", "query": "90s track jacket in size M",
     "wardrobe": "example", "criterion": 5, "tries": 1},
    {"name": "filters: shoe size", "query": "platform sneakers size 8",
     "wardrobe": "example", "criterion": 5, "tries": 1},
    {"name": "filters: price 2", "query": "denim jacket under $50",
     "wardrobe": "example", "criterion": 5, "tries": 1},
    {"name": "filters: L not XL", "query": "vintage crewneck size L",
     "wardrobe": "example", "criterion": 5, "tries": 1},
    {
        # A user with nothing saved. One of unit 4's three failure modes.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
