"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import suggest_outfit, create_fit_card, query_keywords
from mcp_client import call_tool, MCPError
from generate import ModelUnavailable  # noqa: F401 — handled in unit 4


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
        "steps": [],                 # tool names, in the order they ran
        "tool_inputs": {},           # what each tool was actually called with
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)

    # Each pass round the loop runs one step and picks the next one from what
    # that step put in the session. "done" ends it.
    step = "parse"
    count = 0
    while step != "done":
        count += 1
        trace.check_iterations(count)

        if step == "parse":
            session["parsed"] = parse_query(query)
            if not query_keywords(session["parsed"]["description"]):
                # Branch 2: nothing to search for — only a price or a size.
                session["error"] = (
                    "I can see your price or size, but not what kind of item you "
                    "want. Add a word for the item, e.g. 'graphic tee under $30' "
                    "or 'denim jacket size M'."
                )
                step = "done"
            else:
                step = "search"

        elif step == "search":
            parsed = session["parsed"]
            session["tool_inputs"]["search_listings"] = dict(parsed)
            try:
                session["search_results"] = _search(
                    parsed["description"], parsed["size"], parsed["max_price"]
                )
            except MCPError as exc:
                session["error"] = (
                    "The listing search couldn't be reached, so nothing was "
                    f"searched. Try again in a moment. ({str(exc).splitlines()[0]})"
                )
                step = "done"
                continue
            session["steps"].append("search_listings")

            # Branch 1: empty search — stop and say what to change.
            if not session["search_results"]:
                session["error"] = explain_no_results(parsed)
                step = "done"
            else:
                session["selected_item"] = session["search_results"][0]
                step = "suggest"

        elif step == "suggest":
            item = session["selected_item"]
            session["tool_inputs"]["suggest_outfit"] = {"new_item": item}
            session["outfit_suggestion"] = suggest_outfit(item, session["wardrobe"])
            session["steps"].append("suggest_outfit")
            step = "fit_card"

        elif step == "fit_card":
            item = session["selected_item"]
            session["tool_inputs"]["create_fit_card"] = {
                "outfit": session["outfit_suggestion"],
                "new_item": item,
            }
            session["fit_card"] = create_fit_card(session["outfit_suggestion"], item)
            session["steps"].append("create_fit_card")
            step = "done"

    return session


def _search(description: str, size: str | None, max_price: float | None) -> list[dict]:
    """search_listings, called through the MCP server in mcp_server.py."""
    return call_tool("search_listings", {
        "description": description,
        "size": size,
        "max_price": max_price,
    })


# ── query parsing ─────────────────────────────────────────────────────────────

_PRICE = re.compile(
    r"(?:under|below|less than|at most|max(?:imum)?|up to|<)\s*\$?\s*(\d+(?:\.\d+)?)"
    r"|\$\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_SIZE = re.compile(
    r"(?:\bin\s+)?\bsize\s+((?:us\s*)?[a-z]*\d+(?:\.\d+)?|xxs|xs|s|m|l|xl|xxl)\b",
    re.IGNORECASE,
)


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a max_price out of plain language, by regex.

        "vintage graphic tee under $30, size M"
            → {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}

    A bare "$30" is read as a ceiling. Whatever isn't price or size is the
    description.
    """
    text = query
    max_price = None
    m = _PRICE.search(text)
    if m:
        max_price = float(m.group(1) or m.group(2))
        text = text[: m.start()] + " " + text[m.end():]

    size = None
    m = _SIZE.search(text)
    if m:
        size = re.sub(r"(?i)^us\s*", "", m.group(1)).upper()
        text = text[: m.start()] + " " + text[m.end():]

    description = re.sub(r"[^\w\s'-]", " ", text)
    description = " ".join(description.split())
    return {"description": description, "size": size, "max_price": max_price}


def explain_no_results(parsed: dict) -> str:
    """
    Say which filter emptied the search, by re-running it without each one.
    No model call — the same query always gets the same message.
    """
    desc, size, price = parsed["description"], parsed["size"], parsed["max_price"]
    asked = f"'{desc}'" + (f" in size {size}" if size else "") + (
        f" under ${price:.0f}" if price is not None else ""
    )

    without_price = _search(desc, size, None) if price is not None else []
    without_size = _search(desc, None, price) if size else []
    words_only = _search(desc, None, None)

    if without_price:
        cheapest = min(without_price, key=lambda l: l["price"])
        return (
            f"Nothing matched {asked}. The price is what's ruling it out: the "
            f"cheapest match is {cheapest['title']} at ${cheapest['price']:.0f}. "
            f"Try raising your budget to ${cheapest['price']:.0f}."
        )
    if without_size:
        sizes = sorted({l["size"] for l in without_size})
        return (
            f"Nothing matched {asked}. The size is what's ruling it out — matches "
            f"exist in {', '.join(sizes[:5])}. Try a different size, or leave the size out."
        )
    if words_only:
        cheapest = min(words_only, key=lambda l: l["price"])
        return (
            f"Nothing matched {asked}. Size and price together rule everything "
            f"out. Without them the closest match is {cheapest['title']} "
            f"(size {cheapest['size']}, ${cheapest['price']:.0f}). Try dropping the "
            f"size or raising the budget."
        )
    return (
        f"Nothing matched {asked}. No listing uses the words '{desc}', so it's "
        f"the wording, not your size or budget. Try a plainer word for the item "
        f"(tee, jeans, jacket, sneakers, bag) or a style (vintage, y2k, grunge, 90s)."
    )


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
