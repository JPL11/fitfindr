# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
I picked 4 of 5, not 5 of 5, because two of the three calls go to a model on
the free tier. A rate-limit error that runs out of retries, or a blocked
response, can end one try even when my search and loop are fine. The search
itself doesn't vary run to run (it's a plain keyword match over a fixed file),
so if this misses by more than one it points at the model calls.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
This path never calls the model. It's `search_listings` returning `[]` and
an `if` in `run_agent`, and both are deterministic. The same query gives the
same result every time, so anything below 5 of 5 means the branch is broken.
It isn't noise. "Naming what to change" means the message names at least one
of the price, the size or the wording, e.g. "nothing under $5 — the cheapest
match is $38".

---

## 3. The item search picked is the item the next two tools received

Given a matching query, `session["selected_item"]["id"]` equals
`session["search_results"][0]["id"]`, and the same `id` is in the item
`suggest_outfit` received and the item `create_fit_card` received (recorded
in `session["tool_inputs"]`). All three ids agree in 5 of 5 tries.

**Why this target:**
5 of 5, because nothing random sits between search and the next tool call.
The item goes into the session and comes back out as the same dict. If the ids
ever disagree, the loop is reading from the wrong place, for example
re-searching, taking a different index, or letting the user re-type it. That is
a bug, not variation. I compare `id`s rather than titles because two listings
could share a title.

---

## 4. The fit card is postable and names the facts

For the matching query run 5 times with the cache off, the fit card
(a) contains the item's price as `$NN` (e.g. `$24` or `$24.00`), (b) contains
the platform name (case-insensitive), (c) is 400 characters or fewer, and
(d) has at most 3 hashtags. All four hold in at least 4 of 5 tries, and no two
of the 5 cards share the same first sentence.

**Why this target:**
The words are supposed to change from run to run, so I don't check wording.
I check the facts a caption needs (price, platform) and the limits a real post
has (length, not a wall of hashtags). All four are string checks anyone can
do without asking me. I picked 4 of 5 and not 5 of 5 because the prompt asks
for these things but the model at temperature 0.9 sometimes writes "under
thirty bucks" instead of "$24", or goes a bit long. The "no two identical
first sentences" part makes sure the cache is off and the temperature isn't 0.

> **Revised in unit 4:** For the matching query run 5 times with the cache
> off, the fit card (a) contains the item's price as `$NN`, (b) contains the
> platform name, (c) is 400 characters or fewer, and (d) has **1 to 3
> hashtags, each written with `#`**. All four hold in at least 4 of 5 tries,
> and **no more than 2 of the 5 cards open with the same first two words**.
>
> **Why revised:** The original scored 5/5 and still let through what I'd be
> unhappy to see, so it was measuring the wrong thing.
> (1) "At most 3 hashtags" only counts words starting with `#`. A card ending
> `vintage streetwear bandtee` (tags typed without `#`, which happened in
> 3 of the 5 criterion-4 tries) counted as zero hashtags and passed, but you
> can't post that. (2) "No two share the same first sentence" can't see a
> template. 4 of the 5 cards opened "Scored this … on depop for just $19",
> and they only differed by an adjective in the middle, so exact-sentence
> matching called them all different. Counting shared two-word openers is
> something I can score, and it catches the template.

---

## 5. Search respects the price ceiling and size

For these 5 queries, every listing in `session["search_results"]` has
`price <= max_price` and a size that passes the size rule in the README
(whole-token match, so `L` never returns `XL` and `S` never returns
`US 9`): `vintage graphic tee under $30`, `90s track jacket in size M`,
`platform sneakers size 8`, `denim jacket under $50`,
`vintage crewneck size L`. 5 of 5 queries, with zero violating listings in
any of them. At least one result must come back for each query, so an empty list can't pass.

**Why this target:**
A thrift agent that shows a $45 jacket to someone who said "under $30", or
shoes to someone who asked for a small top, is simply wrong, however good the
caption is. This criterion tests the query parsing (regex) and the filter in
`search_listings`. Neither is random, so the target is 5 of 5. The last query
is there on purpose to catch the `"l" in "xl"` substring bug the starter warns
about: both crewnecks in the data are `XL`, so a substring filter would let
them through.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
