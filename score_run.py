#!/usr/bin/env python3
"""
Score a run_eval.py log against criteria.md, exactly as the criteria are written.

    python score_run.py results/run_..._before.json

run_eval.py leaves the PASS/FAIL cells blank on purpose. This fills them in
mechanically from the saved sessions, one check per criterion, and prints the
run-log table plus the reason for every FAIL — so a verdict can be traced back
to the session that produced it.
"""

import json
import re
import sys

from tools import _size_matches


def c1(s):
    ok = (not s["error"] and bool(s["fit_card"])
          and s["steps"] == ["search_listings", "suggest_outfit", "create_fit_card"])
    return ok, "" if ok else f"error={s['error']!r} steps={s['steps']}"


def c2(s):
    msg = (s["error"] or "").lower()
    names_change = any(w in msg for w in ("budget", "size", "word"))
    ok = (bool(s["error"]) and "suggest_outfit" not in s["steps"]
          and s["outfit_suggestion"] is None and s["fit_card"] is None and names_change)
    return ok, "" if ok else f"steps={s['steps']} error={s['error']!r}"


def c3(s):
    if s["error"]:
        return False, f"run stopped: {s['error']}"
    ids = [s["selected_item"]["id"], s["search_results"][0]["id"],
           s["tool_inputs"]["suggest_outfit"]["new_item"]["id"],
           s["tool_inputs"]["create_fit_card"]["new_item"]["id"]]
    return len(set(ids)) == 1, f"ids={ids}"


def c4_checks(s):
    card = s["fit_card"] or ""
    item = s["selected_item"] or {}
    price = item.get("price", -1)
    fails = []
    if not re.search(rf"\$\s?{int(price)}(?:\.00)?(?!\d)", card):
        fails.append(f"(a) no ${int(price)}")
    if (item.get("platform") or "?").lower() not in card.lower():
        fails.append(f"(b) no platform {item.get('platform')}")
    if len(card) > 400:
        fails.append(f"(c) {len(card)} chars")
    tags = re.findall(r"#\w+", card)
    if len(tags) > 3:
        fails.append(f"(d) {len(tags)} hashtags")
    return fails


def first_sentence(card):
    return re.split(r"(?<=[.!?])\s", (card or "").strip(), maxsplit=1)[0].strip().lower()


def c5(s, query):
    from agent import parse_query
    parsed = parse_query(query)
    results = s["search_results"]
    if not results:
        return False, "no results"
    bad = [r["id"] for r in results
           if (parsed["max_price"] is not None and r["price"] > parsed["max_price"])
           or (parsed["size"] and not _size_matches(parsed["size"], r["size"]))]
    return not bad, f"{len(results)} results" + (f", violating: {bad}" if bad else ", 0 violating")


TARGETS = {1: (4, "4 of 5"), 2: (5, "5 of 5"), 3: (5, "5 of 5"), 4: (4, "4 of 5"), 5: (5, "5 of 5")}
NAMES = {1: "Matching query completes all three tools",
         2: "Impossible query stops before suggest_outfit",
         3: "Selected item id reaches both later tools",
         4: "Fit card has price + platform, ≤400 chars, ≤3 hashtags",
         5: "Search results respect price and size"}


def main(path):
    rows = json.load(open(path, encoding="utf-8"))
    cells = {n: [] for n in TARGETS}
    notes = {n: [] for n in TARGETS}
    cards = []

    for row in rows:
        sc, n = row["scenario"], row["scenario"].get("criterion")
        if n is None:
            continue
        for t in row["tries"]:
            s = t["session"]
            if t["crashed"] or s is None:
                ok, why = False, f"crashed: {t['crashed']}"
            elif n == 1:
                ok, why = c1(s)
            elif n == 2:
                ok, why = c2(s)
            elif n == 3:
                ok, why = c3(s)
            elif n == 4:
                fails = c4_checks(s) if s["fit_card"] else ["no fit card"]
                ok, why = not fails, ", ".join(fails)
                cards.append(s["fit_card"])
            else:
                ok, why = c5(s, sc["query"])
                why = f"{sc['query']!r}: {why}"
            cells[n].append("PASS" if ok else "FAIL")
            notes[n].append(why)

    firsts = [first_sentence(c) for c in cards if c]
    dupes = len(firsts) != len(set(firsts))

    print("| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |")
    print("|---|---|---|---|---|---|---|---|")
    for n, (need, target) in TARGETS.items():
        passes = cells[n].count("PASS")
        met = passes >= need and not (n == 4 and dupes)
        verdict = f"{'MET' if met else 'MISSED'} ({passes}/{len(cells[n])})"
        if n == 4 and dupes:
            verdict += ", repeated first sentence"
        print(f"| {n}. {NAMES[n]} | {target} | {' | '.join(cells[n])} | {verdict} |")

    print("\nPer-try notes:")
    for n in TARGETS:
        for i, (c, why) in enumerate(zip(cells[n], notes[n]), 1):
            print(f"  {n}.{i} {c} {why}")
    print("\nCriterion 4 first sentences:")
    for f in firsts:
        print(f"  - {f}")
    print(f"  all different: {not dupes}")


if __name__ == "__main__":
    main(sys.argv[1])
