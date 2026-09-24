"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# Words that say nothing about the item itself. Without this list "looking for
# a tee" would score every listing whose description contains "a".
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "of", "to", "on",
    "i", "im", "i'm", "me", "my", "want", "wants", "need", "looking", "look",
    "find", "some", "something", "any", "that", "is", "it", "size", "under",
    "below", "less", "than", "max", "around", "cheap", "please",
}

# A few spellings the data uses one way and people type another.
_SYNONYMS = {
    "tshirt": "tee", "t-shirt": "tee", "shirt": "tee", "tees": "tee",
    "sneaker": "sneakers", "boot": "boots", "jean": "jeans",
    "pant": "pants", "trouser": "trousers",
}

_LETTER_SIZES = {"xxs", "xs", "s", "m", "l", "xl", "xxl"}


def _words(text: str) -> list[str]:
    """Lower-case words, with the synonyms folded together."""
    out = []
    for w in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", text.lower()):
        w = _SYNONYMS.get(w, w)
        out.append(w)
        # "graphic-tee" / "long-sleeve" also count as their halves
        if "-" in w:
            out.extend(_SYNONYMS.get(part, part) for part in w.split("-"))
    return out


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    Whole-token size match. The listing size is split on "/", spaces and
    parentheses, and `wanted` has to equal one of the pieces.

        "M"  matches "M", "S/M", "M/L"
        "L"  does NOT match "XL"         ("l" in "xl" is a substring bug)
        "S"  does NOT match "US 9"
        "8"  matches "US 8" but not "US 8.5"

    "One Size" listings fit any letter size.
    """
    wanted = wanted.strip().lower().removeprefix("us").strip()
    tokens = [t for t in re.split(r"[\s/()]+", listing_size.lower()) if t]
    if "one" in tokens and "size" in tokens:
        return wanted in _LETTER_SIZES
    return wanted in tokens


def _score(listing: dict, keywords: list[str]) -> int:
    title = set(_words(listing["title"]))
    tags = set(_words(" ".join(listing.get("style_tags") or [])))
    category = set(_words(listing.get("category") or ""))
    other = set(_words(
        " ".join(listing.get("colors") or [])
        + " " + (listing.get("brand") or "")
        + " " + (listing.get("description") or "")
    ))
    score = 0
    for kw in keywords:
        if kw in title:
            score += 4
        elif kw in tags:
            score += 3
        elif kw in category or kw.rstrip("s") in category:
            score += 2
        elif kw in other:
            score += 1
    return score


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    keywords = [w for w in _words(description or "") if w not in _STOPWORDS]
    if not keywords:
        return []

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not _size_matches(size, listing["size"]):
            continue
        score = _score(listing, keywords)
        if score > 0:
            scored.append((score, listing))

    # Highest score first; ties go to the cheaper listing.
    scored.sort(key=lambda pair: (-pair[0], pair[1]["price"]))
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    item_text = _describe_item(new_item)
    items = (wardrobe or {}).get("items") or []

    system = (
        "You are a thrift stylist. Be concrete and brief. Plain text, no "
        "markdown headings, no more than two outfits."
    )

    if not items:
        prompt = (
            f"Someone is thinking about buying this thrifted piece:\n{item_text}\n\n"
            "They haven't told us what's in their wardrobe. Give general styling "
            "ideas: two outfits, each naming the kinds of pieces (e.g. 'straight "
            "dark jeans', 'white sneakers') that pair with it and why. "
            "Two or three sentences per outfit."
        )
        return "No saved wardrobe yet — general ideas: " + generate(prompt, system=system).strip()

    wardrobe_lines = "\n".join(
        f"- {w['name']} ({w.get('category')}; colors: {', '.join(w.get('colors') or [])}"
        f"; style: {', '.join(w.get('style_tags') or [])})"
        + (f" — note: {w['notes']}" if w.get("notes") else "")
        for w in items
    )
    prompt = (
        f"Someone is thinking about buying this thrifted piece:\n{item_text}\n\n"
        f"This is what they already own:\n{wardrobe_lines}\n\n"
        "Suggest two outfits built around the new piece, using only pieces from "
        "their wardrobe list. Name each wardrobe piece exactly as it is written "
        "above. One or two sentences per outfit on why it works."
    )
    return generate(prompt, system=system).strip()


def _describe_item(item: dict) -> str:
    """The listing as a few lines of prompt text. Brand is often None — skip it then."""
    lines = [
        f"Title: {item.get('title')}",
        f"Category: {item.get('category')}",
        f"Colors: {', '.join(item.get('colors') or [])}",
        f"Style: {', '.join(item.get('style_tags') or [])}",
        f"Size: {item.get('size')}  Condition: {item.get('condition')}",
        f"Price: ${item.get('price', 0):.0f} on {item.get('platform')}",
    ]
    if item.get("brand"):
        lines.insert(1, f"Brand: {item['brand']}")
    return "\n".join(lines)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return (
            "Couldn't write a fit card: no outfit suggestion was provided for "
            f"{new_item.get('title', 'this item')}."
        )

    price = f"${new_item.get('price', 0):.0f}"
    platform = new_item.get("platform")
    system = (
        "You write captions for outfit posts. Casual, specific, first person. "
        "No markdown, no quotation marks around the caption."
    )
    prompt = (
        f"The thrifted find:\n{_describe_item(new_item)}\n\n"
        f"How I'm styling it:\n{outfit}\n\n"
        "Write the caption for my post about this fit. Rules:\n"
        "- 2 to 4 sentences, under 400 characters total.\n"
        f"- Mention the item, the price written exactly as {price}, and "
        f"{platform} — each once.\n"
        "- Say something specific about the vibe of the outfit, not a product description.\n"
        "- At most 3 hashtags, at the end."
    )
    return generate(prompt, system=system).strip()
