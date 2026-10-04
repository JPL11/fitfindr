# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

A user types what they're thrifting for in plain language, like
`vintage graphic tee under $30` or `platform sneakers size 8`. FitFindr pulls
the item words, size and price ceiling out of that sentence and searches 40
listings from Depop, thredUp and Poshmark. It picks the best match and asks
the model for two outfits built from the user's saved wardrobe, then writes a
short caption for posting the fit. If nothing matches, it stops before
calling the model and says which part of the request to change: the budget,
the size, or the wording.


---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

Listing fields (from `python app.py fields`): `id`, `title`, `description`,
`category`, `style_tags` (list), `size`, `condition`, `price` (float),
`colors` (list), `brand` (str or None — None for most listings), `platform`.
Sizes in the data are mixed: letter sizes (`M`, `S/M`, `L/XL`,
`XL (oversized)`), waist sizes (`W28`, `W30 L30`), shoe sizes (`US 8.5`) and
`One Size`. An empty wardrobe is `{"items": []}`.

### `search_listings`

- **What it does:** Filters `data/listings.json` by price ceiling and size, then ranks what is left by keyword overlap with the description.
- **Inputs:** `description` (str) — keywords like `"vintage graphic tee"`; `size` (str or None) — `None` skips the size filter; `max_price` (float or None) — inclusive ceiling, `None` skips the price filter.
- **Returns:** A `list[dict]` of at most `config.SEARCH_RESULT_LIMIT` (10) listing dicts, best match first. Each dict is the full listing with the fields above, unchanged — `id`, `title`, `price`, `size`, `platform` and the rest. Ranking: each query word scores 4 if it is in the title, else 3 in a style tag, else 2 in the category, else 1 in a color, the brand or the description; anything scoring 0 is dropped.
- **Size rule:** the listing size is split on `/`, spaces and parentheses into whole tokens, and the requested size must equal one of them, case-insensitively. So `M` matches `M`, `S/M`, `M/L`, but `L` does **not** match `XL`, `S` does not match `US 9`, and `8` matches `US 8` but not `US 8.5`. `One Size` listings match any letter size (XS–XXL).
- **When it has nothing:** an empty list `[]` — never `None`, never an exception.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the new item, using pieces the user already owns.
- **Inputs:** `new_item` (dict) — one listing dict from `search_listings`; `wardrobe` (dict) — `{"items": [wardrobe item dicts]}`, where each item has `id`, `name`, `category`, `colors`, `style_tags`, `notes`.
- **Returns:** a non-empty `str` of outfit suggestions, 2 outfits max, each naming the wardrobe pieces by their `name`.
- **When it has nothing:** if `wardrobe["items"]` is empty (or missing), it does not fail — it asks the model for general styling advice for the item (what kinds of pieces pair with it) and returns that string, starting with `No saved wardrobe yet — general ideas:`.

### `create_fit_card`

- **What it does:** Asks the model for a short social-media caption about the find and the outfit.
- **Inputs:** `outfit` (str) — the string `suggest_outfit` returned; `new_item` (dict) — the same listing dict.
- **Returns:** a `str` caption of 2–4 sentences (under 400 characters requested) that names the item, its price as `$NN` and its platform once each, and says something about the outfit's vibe. At most 3 hashtags.
- **When it has nothing:** if `outfit` is empty or only whitespace, it does not call the model and returns the string `Couldn't write a fit card: no outfit suggestion was provided for <item title>.`

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in
`session["error"]` that names which filter to loosen (price, size, or wording —
worked out by re-checking the search without each one) and stop, leaving
`selected_item`, `outfit_suggestion` and `fit_card` as `None`. Otherwise take
the first (highest-scoring) result as `session["selected_item"]` and go on to
`suggest_outfit`, then `create_fit_card`.

**Second branch (stretch):** If parsing leaves no description words at all
(e.g. the query was just `under $30`), stop before searching and ask the user
what kind of item they want, instead of returning every listing under $30.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, in `agent.py::parse_query`, with no model
call. `under/below/less than/max/up to $N` (or a bare `$N`) becomes
`max_price`. `size X` / `in size X` becomes `size` (a leading `US` is
dropped, so `size US 8` → `8`). Whatever is left is the `description`.

**How the loop runs:** `run_agent` is a `while step != "done"` loop. Each pass
runs one step (`parse` → `search` → `suggest` → `fit_card`), and the step
picks the next one from what it just put in the session. Every pass calls
`trace.check_iterations(count)` first.

**The empty-search message:** `agent.py::explain_no_results` re-runs the
search without the price, then without the size, then with the words only.
From that it tells the user which filter emptied the results, e.g.
*"The price is what's ruling it out: the cheapest match is Platform
Sneakers — White Chunky Sole at $48. Try raising your budget to $48."*

**What moves through the session:** in order:
`query` → `parsed` (`description`, `size`, `max_price`) →
`search_results` (list of listing dicts) → `selected_item`
(`search_results[0]`) → `outfit_suggestion` → `fit_card`. `steps` records
which tools ran, and `tool_inputs` records exactly what each tool was called
with. That is how criterion 3 checks that `selected_item` is the item
`suggest_outfit` and `create_fit_card` received. On an early stop `error` is
set and `selected_item`, `outfit_suggestion` and `fit_card` stay `None`.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

  Found:    Vintage Band Tee — Faded Grey — $19.0 on depop

  Outfit:   Outfit One
Baggy straight-leg jeans, dark wash
Vintage Band Tee — Faded Grey
Vintage black denim jacket
Black combat boots
Black crossbody bag

This works because the dark denim and combat boots lean into the vintage grunge vibe, while the cropped jacket balances the oversized tee.


Outfit Two
Wide-leg khaki trousers
Vintage Band Tee — Faded Grey
Brown leather belt
Chunky white sneakers
Black crossbody bag

This works by pairing the relaxed band tee with tailored earth-toned trousers for an effortless, high-low streetwear look.

  Fit card: Scored this faded grey band tee on depop for just $19 and I am so obsessed with how it looks dressed down with baggy dark denim and combat boots. It gives off the absolute best effortless grunge energy, but I also love pairing it with tailored khakis for a slouchy high low mix. vintagebandtee grunge streetwear

$ python app.py ask 'designer ballgown size XXS under $5'

  Nothing matched 'designer ballgown' in size XXS under $5. No listing uses the words 'designer ballgown', so it's the wording, not your size or budget. Try a plainer word for the item (tee, jeans, jacket, sneakers, bag) or a style (vintage, y2k, grunge, 90s).

0 model calls this session

$ python -c "from agent import run_agent; from utils.data_loader import get_example_wardrobe as w; s=run_agent('vintage graphic tee under \$30', w()); print(s['selected_item']['id'], s['search_results'][0]['id'], s['tool_inputs']['suggest_outfit']['new_item']['id'], s['tool_inputs']['create_fit_card']['new_item']['id'], s['steps'])"
lst_033 lst_033 lst_033 lst_033 ['search_listings', 'suggest_outfit', 'create_fit_card']
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30)[0])"
{'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}

$ python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
[]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[5], get_example_wardrobe()))"
Outfit 1:
Graphic Tee — 2003 Tour Bootleg Style
Baggy straight-leg jeans, dark wash
Vintage black denim jacket
Black combat boots
Black crossbody bag

This works because it leans fully into a cohesive grunge streetwear aesthetic using matching black denim and rugged boots.


Outfit 2:
Graphic Tee — 2003 Tour Bootleg Style
Wide-leg khaki trousers
Brown leather belt
Chunky white sneakers
Black crossbody bag

This works by pairing the edgy graphic top with clean earth tones to create a balanced, casual streetwear look.

$ python -c "from tools import suggest_outfit; from utils.data_loader import get_empty_wardrobe, load_listings; print(suggest_outfit(load_listings()[5], get_empty_wardrobe()))"
No saved wardrobe yet — general ideas: Outfit 1: Pair the tee with baggy distressed light-wash denim and chunky black skate sneakers for an authentic 90s grunge look. Layer an oversized plaid flannel shirt unbuttoned over top to add depth and tie the effortless streetwear vibe together.

Outfit 2: Tuck the tee into a black pleated tennis skirt and add knee-high combat boots for a sharp contrast of edgy and feminine styles. Finish with a beat-up leather moto jacket draped over the shoulders to lean fully into the vintage tour aesthetic.
```

Run three times with the cache off (`AI201_CACHE=0`), to check the captions
actually vary:

```
$ AI201_CACHE=0 python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('Tee with baggy dark jeans, black combat boots and a black denim jacket', load_listings()[5]))"
Scored this bootleg tour tee for $24 on depop and haven't taken it off since. Paired it with baggy dark denim and heavy combat boots for that effortless 90s grunge look. Channeling total concert-aftermath energy today. #grunge #bandtee #streetwear
---
scored this vintage bootleg tour tee for $24 on depop and it is instantly my favorite piece. pairing it with baggy denim and combat boots gives off such an effortlessly heavy grunge energy. perfect for shuffling around the city on a overcast afternoon.

#grunge #depop #streetwear
---
Scored this bootleg tour tee for $24 on depop and it is the ultimate grunge staple. Paired it with baggy dark denim and heavy boots for that effortlessly worn-in streetwear look. The faded graphics give it instant character. streetwear grunge vintage

$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('   ', load_listings()[5]))"
Couldn't write a fit card: no outfit suggestion was provided for Graphic Tee — 2003 Tour Bootleg Style.
```

The three captions differ, but all three open with "Scored this", and one
dropped the `#` from its hashtags. Both are worth checking against
criterion 4 in unit 4.

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

I used Claude Code for this build.

**Moment 1**

- *What I asked for:* `search_listings` built from my Tool Inventory spec:
  keyword-overlap scoring, a whole-token size match, and `[]` on no match.
- *What came back:* A working search where a title word and a style-tag word
  both scored 3. I tested `search_listings('vintage crewneck', size='L')` and
  the size filter was right (both `XL` crewnecks were excluded). But the top
  two results were a braided belt and a bucket hat. They are `One Size`, carry
  the `vintage` tag, and tied with the tees, so the cheaper price sorted them
  first.
- *What I changed:* I raised title matches to 4, so a word in the title beats
  the same word in a tag. The top results became the band tee and the graphic
  hoodie. I updated the ranking line in the Tool Inventory to match.

**Moment 2**

- *What I asked for:* For each criterion, how it could be tested using only
  the sentence as written.
- *What came back:* Criterion 5 listed `jeans size L under $40` as one of its
  test queries. Every pair of jeans in the data has a waist size (`W28`,
  `W30 L30`, …), so that search returns `[]`. "Every result respects the size"
  would then pass on an empty list without testing anything.
- *What I changed:* I swapped that query for `vintage crewneck size L`. The
  only crewnecks are `XL`, so this catches the `"l" in "xl"` substring bug.
  I also added "at least one result must come back for each query", so an
  empty list can't pass.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

`python run_eval.py --label before`, with the cache off. The full log is
[`results/run_2026-10-04_1218_before.md`](results/run_2026-10-04_1218_before.md),
plus the raw sessions in the matching `.json`. PASS/FAIL comes from
`python score_run.py results/run_2026-10-04_1218_before.json`, which applies
each criterion in `criteria.md` as written. For criteria 1–4 the five tries
are five runs of the same query. For criterion 5 they are the five queries
the criterion names, run once each (the search is deterministic).

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before suggest_outfit | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Selected item id reaches both later tools | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card has price + platform, ≤400 chars, ≤3 hashtags, no repeated first sentence | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Search results respect price and size | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4R. *(criterion 4 as revised — see below)* 1–3 `#`hashtags, ≤2 of 5 share an opener | 4 of 5 | PASS | FAIL | PASS | FAIL | FAIL | MISSED (2/5), 4/5 open "scored this" |

**Real output, one try per criterion.** All of it was produced by
`agent.py::run_agent` (the trace) under `run_eval.py::run_once`.

*Criterion 1, try 1* (`vintage graphic tee under $30`): all three tools ran,
and `tools.py::create_fit_card` returned:

```
Scored this faded vintage band tee on depop for just $19 and I am so obsessed with how buttery soft it feels. Tucking it into these crisp khaki trousers totally tones down the heavy grunge energy for a way more balanced everyday look. The brown leather belt and fresh white sneaks pull the whole casual shape together. vintagefashion streetwear outfitinspo
```

*Criterion 2, try 1*:

```
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: description='designer ballgown', size='XXS', max_price=5.0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
[3] branch
      →    empty search — stopping before suggest_outfit
error: Nothing matched 'designer ballgown' in size XXS under $5. No listing uses the words 'designer ballgown', so it's the wording, not your size or budget. Try a plainer word for the item (tee, jeans, jacket, sneakers, bag) or a style (vintage, y2k, grunge, 90s).
```

*Criterion 3, try 1* (`denim jacket under $50`). `score_run.py::c3`
compared `selected_item`, `search_results[0]`, and what
`tool_inputs` recorded going into `suggest_outfit` and `create_fit_card`:
`ids=['lst_007', 'lst_007', 'lst_007', 'lst_007']`.

```
[2] search_listings (via MCP)
      in:  description='denim jacket', size=None, max_price=50.0
      out: 7 items: Denim Jacket — Light Wash, Cropped, High-Waisted Denim Shorts — Cutoff, Denim Vest — Medium Wash, Studded … +4 more
[3] select_item
      out: Denim Jacket — Light Wash, Cropped ($42.0, poshmark)
      →    took result 1 of 7 (lst_007)
[4] suggest_outfit
      in:  Denim Jacket — Light Wash, Cropped (lst_007) + wardrobe of 10 items
      out: Outfit One: White ribbed tank top, Baggy straight-leg jeans, and Chunky white sneakers.  The cropped Wrangler …
[5] create_fit_card
      in:  outfit (479 chars) + lst_007
      out: Scored this vintage Wrangler denim jacket on Poshmark for just $42 and honestly haven't taken it off since. Lo…
```

*Criterion 4, all five cards* (same query, cache off):

```
1. Scored this faded graphic tee on depop for just $19 and I am so obsessed with how perfectly broken in it is. Paired it with dark denim and combat boots for an effortlessly cool grunge vibe that feels super easy to throw on. #vintagestyle #grungeaesthetic #streetwear
2. Scored this amazing vintage band tee on depop for just $19 and it has the absolute best worn-in fade. Paired it with baggy denim and heavy boots for a gritty, effortless look that feels straight out of the nineties. Grunge style is just too easy when the pieces do all the talking. streetwear vintage outfit
3. Scored this vintage band tee on depop for just $19 and I am so obsessed with how it looks dressed down with baggy denim and heavy boots. The faded wash gives it that genuinely lived-in feel that brand new shirts just cannot replicate. #grunge #vintagestyle #streetwear
4. Scored this perfectly faded band tee on depop for just $19 and I am obsessed with the grunge energy. I love dressing it down with baggy denim and combat boots for that effortless 90s streetwear look. vintage streetwear bandtee
5. Found this faded grey band tee on depop for $19 and it instantly became my go-to for effortless grunge streetwear. Paired it with baggy denim and heavy boots for that broken-in 90s feel. Total thrift score. vintage streetwear grungy
```

*Criterion 5, try 5* (`vintage crewneck size L`): `8 results, 0 violating`.
Both crewnecks in the data are `XL` and neither came back:

```
[2] search_listings (via MCP)
      in:  description='vintage crewneck', size='L', max_price=None
      out: 8 items: Vintage Band Tee — Faded Grey, Vintage Graphic Hoodie — Faded Black, Vintage Linen Blazer — Cream … +5 more
```

---

## Verdicts and Diagnoses

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | Matching query completes all three tools | 4 of 5 | MET (5/5) | Each try had `error=None`, a non-empty `fit_card`, and `steps` equal to the three tool names in order |
| 2 | Impossible query stops before suggest_outfit | 5 of 5 | MET (5/5) | `steps == ['search_listings']`, `outfit_suggestion` and `fit_card` both `None`, and the message names what to change (it says "word") |
| 3 | Selected item reaches both later tools | 5 of 5 | MET (5/5) | All four ids were `lst_007` in every try |
| 4 | Fit card is postable (original wording) | 4 of 5 | MET (5/5) | All five cards had `$19`, `depop`, ≤400 chars (228–307), ≤3 `#` tags, and five different first sentences. **But see the revision**: the verdict is MET and still wrong about what I cared about |
| 4R | Fit card (revised in `criteria.md`) | 4 of 5 | MISSED (2/5) | Tries 2, 4 and 5 have zero `#` hashtags (their tags are bare words), and 4 of 5 open with "scored this" |
| 5 | Search respects price and size | 5 of 5 | MET (5/5) | Every result for all five queries was within `max_price` and passed the size rule. Each query returned ≥1 result |

**Nothing missed against the unit 3 targets, and some of those targets were
too low.** Criterion 1 at 4 of 5 was a hedge for rate-limit failures. The
starter's pacing and retries absorbed every limit hit (the run paused four
times and never failed), so 5 of 5 is the honest target now. Criteria 2, 3
and 5 test deterministic code, and 5/5 is what they should get. They
confirm the branch, the session and the filters work. They were never likely
to miss.

**Criterion 4 is the one I'd tighten, and did** (revision written under the
original in `criteria.md`, original left in place). Reading the cards instead
of counting them showed two things the original wording passed:

- **Diagnosis, 4R part (d), the hashtags.** Place: the **model's output**,
  caused by the **prompt** in `tools.py::create_fit_card`. Mechanism: the
  prompt says *"At most 3 hashtags, at the end."* It never says a hashtag
  starts with `#`, and "at most" allows zero. So at temperature 0.9 the model
  ends about half the cards with a run of bare words (`vintage streetwear
  bandtee`). Across all 20 cards in the run, only 12 had 1–3 real `#`
  hashtags. The tool, the loop and the session are fine: the same item and
  outfit went in every time (criterion 3).
- **Diagnosis, 4R openers.** Same place, same prompt. Mechanism: the prompt's
  one content rule is *"Mention the item, the price written exactly as $19,
  and depop — each once"*, and the system line asks for first person. The
  cheapest way to satisfy all of that is one opening clause: "Scored this
  [item] on depop for just $19". 19 of the 20 cards in the whole run open
  "Scored this", across three different items and both wardrobes. Temperature
  only changes the adjective in the middle.
- **Pattern:** both misses are one problem, the fit-card prompt, not two.
  They show up in every scenario that writes a card, including the
  empty-wardrobe diagnostic run.

**Something no criterion caught.** `vintage crewneck size L` returned a band
tee as the top result. There is no crewneck in size L, and the search scores
any single keyword overlap (`vintage`), so it silently answered a different
question. Criterion 5 passed because it checks the filters, not relevance.
See What's Still Broken.

---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

Produced by `agent.py::run_agent` (the `trace.step()` calls) via
`python app.py ask '...' --trace`. Step 2 is the MCP call.

**Happy path**

```
$ python app.py ask 'vintage graphic tee under $30' --trace
[1] parse_query
      in:  vintage graphic tee under $30
      out: description='vintage graphic tee', size=None, max_price=30.0
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', size=None, max_price=30.0
      out: 10 items: Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style, Y2K Baby Tee — Butterfly Print … +7 more
[3] select_item
      out: Vintage Band Tee — Faded Grey ($19.0, depop)
      →    took result 1 of 10 (lst_033)
[4] suggest_outfit
      in:  Vintage Band Tee — Faded Grey (lst_033) + wardrobe of 10 items
      out: Outfit One Baggy straight-leg jeans, dark wash Vintage Band Tee — Faded Grey Vintage black denim jacket Black …
[5] create_fit_card
      in:  outfit (534 chars) + lst_033
      out: Scored this faded grey band tee on depop for just $19 and I am so obsessed with how it looks dressed down with…

  Found:    Vintage Band Tee — Faded Grey — $19.0 on depop

  Outfit:   Outfit One
Baggy straight-leg jeans, dark wash
Vintage Band Tee — Faded Grey
Vintage black denim jacket
Black combat boots
Black crossbody bag

This works because the dark denim and combat boots lean into the vintage grunge vibe, while the cropped jacket balances the oversized tee.


Outfit Two
Wide-leg khaki trousers
Vintage Band Tee — Faded Grey
Brown leather belt
Chunky white sneakers
Black crossbody bag

This works by pairing the relaxed band tee with tailored earth-toned trousers for an effortless, high-low streetwear look.

  Fit card: Scored this faded grey band tee on depop for just $19 and I am so obsessed with how it looks dressed down with baggy dark denim and combat boots. It gives off the absolute best effortless grunge energy, but I also love pairing it with tailored khakis for a slouchy high low mix. vintagebandtee grunge streetwear

0 model calls this session, 2 served from cache
```

**Empty search**: three steps instead of five, because it stops at the branch.

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: description='designer ballgown', size='XXS', max_price=5.0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
[3] branch
      →    empty search — stopping before suggest_outfit

  Nothing matched 'designer ballgown' in size XXS under $5. No listing uses the words 'designer ballgown', so it's the wording, not your size or budget. Try a plainer word for the item (tee, jeans, jacket, sneakers, bag) or a style (vintage, y2k, grunge, 90s).

0 model calls this session
```

### The three failure modes, triggered on purpose

**1. Empty search.** Triggered with `designer ballgown size XXS under $5`
(trace above). Handled since unit 3 by the branch in `agent.py::run_agent`
and `agent.py::explain_no_results`. The agent says:

> Nothing matched 'designer ballgown' in size XXS under $5. No listing uses
> the words 'designer ballgown', so it's the wording, not your size or budget.
> Try a plainer word for the item (tee, jeans, jacket, sneakers, bag) or a
> style (vintage, y2k, grunge, 90s).

When the price is what rules things out, e.g. `platform sneakers size 8 under
$20`, it says so instead: *"The price is what's ruling it out: the cheapest
match is Platform Sneakers — White Chunky Sole at $48. Try raising your budget
to $48."*

**2. Empty wardrobe.** Triggered with `--empty-wardrobe`. Handled since unit 3
in `tools.py::suggest_outfit`. There's no crash and no empty string: it
returns general advice and says that's what it is. The trace shows
`wardrobe of 0 items` going into `suggest_outfit`.

```
$ python app.py ask 'denim jacket under $50' --empty-wardrobe
(running with an empty wardrobe)

  Found:    Denim Jacket — Light Wash, Cropped — $42.0 on poshmark

  Outfit:   No saved wardrobe yet — general ideas: Outfit One: Pair the cropped jacket with a black ribbed midi dress and chunky black combat boots. The fitted, dark silhouette of the dress creates a sharp contrast with the boxy, light wash denim, while the boots add a cool streetwear edge.

Outfit Two: Layer it over an oversized white graphic t-shirt and olive green utility trousers, finished off with retro canvas sneakers. This combination plays with proportions, balancing the jacket's cropped length with the relaxed, baggy fit of the pants.

  Fit card: Scored this cropped Wrangler jacket on poshmark for $42 and I am obsessed with the boxy fit against my favorite black midi dress and chunky boots. It gives off such an effortless streetwear vibe with that perfect vintage wash. thriftstyle vintagefashion streetwear

0 model calls this session, 2 served from cache
```

**3. Model unavailable.** Triggered by changing the last character of
`GEMINI_API_KEY` (as an environment override, so `.env` itself wasn't edited)
and asking a query not in the cache, `corduroy pants under $40`.
**Before a handler**, `ModelUnavailable` escaped `run_agent` and `app.py`'s
catch-all printed:

```
ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.
```

That message was readable, but the run's session was lost. The search had
already succeeded, and the user wasn't told so, or that nothing else in their
query was wrong. **Added handler:** `agent.py::_model_down`. It catches
`ModelUnavailable` around both model calls in `run_agent`, keeps what the
session already has, and stops:

```
[1] parse_query
      in:  corduroy pants under $40
      out: description='corduroy pants', size=None, max_price=40.0
[2] search_listings (via MCP)
      in:  description='corduroy pants', size=None, max_price=40.0
      out: 2 items: Corduroy Wide-Leg Pants — Rust, Low-Rise Cargo Pants — Khaki
[3] select_item
      out: Corduroy Wide-Leg Pants — Rust ($32.0, depop)
      →    took result 1 of 2 (lst_005)
[4] suggest_outfit
      out: ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh k…
      →    model unreachable — stopping

  Couldn't reach the AI model during suggest_outfit, so there's no outfit or fit card this time. The search still worked: it found Corduroy Wide-Leg Pants — Rust ($32 on depop). What to try: check GEMINI_API_KEY in your .env file (a single wrong character is enough to break it) and your internet connection, then run the same query again. Model said: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.
```

The MCP server is a fourth thing that can fail. `MCPError` from `call_tool`
is caught in the search step, which ends the run with *"The listing search
couldn't be reached, so nothing was searched. Try again in a moment."*

**On the MCP move:** `search_listings` is registered in
`mcp_server.py` with a description written for an agent that can't see the
code. It gives units (US dollars, inclusive), the exact size-match rule (`L`
doesn't match `XL`), every field of a returned listing, and the empty case
(`[]`, not an error). In `agent.py` the direct call became
`call_tool("search_listings", {...})`, wrapped in `agent.py::_search`. The
empty-search diagnosis in `explain_no_results` goes through the same path. A
failed MCP call (`MCPError`) now ends the run with a message instead of a
stack trace.

Nothing behaved differently afterwards. I called the tool both ways on three
inputs (a normal query, a size-filtered query, an impossible query) and
compared with `==`: `True` all three times, `[]` came back as `[]` and not as
`None` or `"[]"`, and `price` stayed a float. The one visible change is speed.
Each MCP call starts a fresh server process, which adds about a second per
search. The empty path does up to four searches (one plus three diagnostic
re-searches), so it pays that four times.

---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
