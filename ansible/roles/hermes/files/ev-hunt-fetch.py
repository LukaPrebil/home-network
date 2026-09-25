#!/usr/bin/env python3
"""EV hunt: fetch, hard-filter, and report second-hand EV listings.

The hunt monitor runs this script, then judges the survivors against the
damage rules no machine can read (bolt-on zone, pack-untouched). The script
owns what a machine can check: which cars are in scope at all (model, year,
mileage, price bound per route) and the two damage facts the platforms state
outright (deployed airbags, not drivable). Everything else is the brain's job.

Two source facts shape the design and cost time to rediscover:

* schadeautos.nl carries no per-listing damage field. Its "alle airbags oke"
  and "auto is verrijdbaar" strings are labels of the advanced-search form,
  not listing data; a URL without the slug (/nl/schade/personenautos/o/<id>)
  serves that search page instead of the listing. The only per-listing damage
  signal is the dealer's free text in the `bijzonderheden` cell. So airbag and
  drivable state are three-valued here: an explicit bad phrase rejects, an
  explicit good phrase passes, and silence passes with an `unknown` marker for
  the brain to verify at reply time.
* Boonstra states both as tag classes (`vehicle_tags-rijdbaar`,
  `vehicle_tags-verrijdbaar`) plus a `Kenmerken` sentence that often reads
  "Alle airbags oke".

The state file (the seen set) is script-owned and never written by the brain:
one JSON object keyed by listing id holding first-seen, price history, and the
last classification. `--digest` renders the weekly summary from it instead of
fetching.

Read-only and polite: sequential GETs, one per landing page plus one per
candidate detail page, browser User-Agent, no query-string URLs on
schadeautos.nl (its robots.txt disallows them). The monitor never contacts a
seller, never bids, and never writes outside its state directory.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

SCHADEAUTOS = "https://www.schadeautos.nl"

# Elements that never have a closing tag, so the parser must not push them.
VOID_TAGS = frozenset(
    [
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    ]
)

# Damage phrases. Read only the dealer's free-text block, never the options
# list: "Airbag(s) voor + zij" is a feature, not damage. Bad is checked before
# good, because "niet rijdbaar" contains "rijdbaar".
AIRBAG_BAD = re.compile(
    r"airbags?\b[^.]{0,40}?\b(stuk|kapot|defect|geklapt|afgegaan|beschadigd|"
    r"vervangen|verwijderd|open|niet\s+ok)",
    re.IGNORECASE,
)
AIRBAG_GOOD = re.compile(
    r"airbags?[^.]{0,30}?\b(ok|oke|oké|goed|intact|ongebruikt)",
    re.IGNORECASE,
)
# "niet afgegaan" reads as the opposite of "afgegaan", so a negation has to win
# before the damaged-airbag pattern sees the word inside it. Scoped to an
# airbag mention so an unrelated negation elsewhere in the text ("motor niet
# stuk") cannot turn a damaged-airbag line into a good one.
NEGATED_AIRBAG_GOOD = re.compile(
    r"airbags?[^.]{0,30}?niet\s+(?:afgegaan|geopend|beschadigd|stuk|kapot)",
    re.IGNORECASE,
)
# Both the attributive and the predicative form matter: dealers write
# "verrijdbare voorschade" on the card and "is verrijdbaar" in the text.
# Fire and pyrotechnic SRS damage. Both reject outright (EV plan decision 6):
# a fired pretensioner means pyro-fuse and HV-cutoff work. The `schades` row
# lists the components the dealer declares damaged, so anything in it counts.
FIRE_BAD = re.compile(r"\b(?:brandschade|uitgebrand|in\s+brand)\b", re.IGNORECASE)
SRS_BAD = re.compile(r"\b(?:gordelspanners?|pyro-?fuse)\b", re.IGNORECASE)
DRIVABLE_BAD = re.compile(
    r"\b(?:niet\s+(?:rijdbaar|rijdbare|verrijdbaar|verrijdbare|rijdend|rijdende)|"
    r"rijdt\s+niet|loopt\s+niet|motor\s+(?:is\s+)?stuk|blokkeert|wielklem|total\s+loss)\b",
    re.IGNORECASE,
)
DRIVABLE_GOOD = re.compile(
    r"\b(?:rijdbaar|rijdbare|verrijdbaar|verrijdbare|rijdend\s+mee|rijdt|motor\s+loopt)\b",
    re.IGNORECASE,
)


# ── Lightweight DOM ──────────────────────────────────────────────────
#
# An HTMLParser-driven tree rather than regexes: attribute order, whitespace
# and nesting all vary between listings, and a regex that survives the three
# landing pages this script reads today breaks on the next one.


class Node:
    __slots__ = ("tag", "attrs", "children")

    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.children = []


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node(None, {})
        self.stack = [self.root]

    def _open(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, dict(attrs)))

    def handle_endtag(self, tag):
        # Pop to the matching open tag; anything unclosed in between is closed
        # implicitly rather than left on the stack forever.
        for depth in range(len(self.stack) - 1, 0, -1):
            if self.stack[depth].tag == tag:
                del self.stack[depth:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_html(text):
    builder = TreeBuilder()
    builder.feed(text)
    builder.close()
    return builder.root


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Surface a redirect as a status instead of following it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def walk(node):
    for child in node.children:
        if isinstance(child, Node):
            yield child
            yield from walk(child)


def find_all(node, tag=None, cls=None):
    for found in walk(node):
        if tag is not None and found.tag != tag:
            continue
        if cls is not None and cls not in classes(found):
            continue
        yield found


def find_first(node, tag=None, cls=None, node_id=None):
    for found in walk(node):
        if tag is not None and found.tag != tag:
            continue
        if cls is not None and cls not in classes(found):
            continue
        if node_id is not None and found.attrs.get("id") != node_id:
            continue
        return found
    return None


def classes(node):
    return (node.attrs.get("class") or "").split()


def collapse(text):
    return re.sub(r"\s+", " ", text or "").strip()


def text_of(node):
    if node is None:
        return ""
    parts = []

    def collect(current):
        for child in current.children:
            if isinstance(child, str):
                parts.append(child)
            else:
                collect(child)

    collect(node)
    return collapse(" ".join(parts))


def lines_of(node):
    """Text of a node split on <br>, one entry per declared item.

    The declared damage list is <br>-separated, and the item is the unit that
    carries meaning: "alle airbags oké" is a whole item, while an options list
    holds "Airbag(s) voor" as one item among hundreds. Testing the joined text
    instead lets an option sit within a pattern's window of an unrelated damage
    word, and a false bad verdict silently drops a car.
    """
    if node is None:
        return []
    parts = []

    def collect(current):
        for child in current.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag == "br":
                parts.append("\n")
            else:
                collect(child)

    collect(node)
    return [collapse(line) for line in "".join(parts).split("\n") if collapse(line)]


# ── Value parsing ────────────────────────────────────────────────────


def parse_int(text):
    """Pull the first integer out of a price or mileage string.

    Dutch listings use '.' as the thousands separator ("€ 7.450", "114.569"),
    so stripping every non-digit is correct and does not collide with cents.
    """
    if text is None:
        return None
    digits = re.sub(r"[^0-9]", "", text)
    return int(digits) if digits else None


def price_pair(listing_price, export_price):
    """Choose the price to filter on and remember which one it is.

    The purchase bound is a VAT-inclusive listing-price ceiling, so the sale
    price wins whenever the platform states it. Some listings quote only the
    export (net) price; that number is the only one available, and using it
    keeps the car visible instead of marking its price unknown. The alert says
    which one it read.
    """
    if listing_price is not None:
        return listing_price, False
    if export_price is not None:
        return export_price, True
    return None, False


def parse_year(text):
    if text is None:
        return None
    found = re.search(r"\b(19|20)\d{2}\b", text)
    return int(found.group(0)) if found else None


def tri_state(text, bad, good, negated=None):
    if not text:
        return "unknown"
    if negated is not None and negated.search(text):
        return "good"
    if bad.search(text):
        return "bad"
    if good.search(text):
        return "good"
    return "unknown"


def airbag_state(text):
    return tri_state(text, AIRBAG_BAD, AIRBAG_GOOD, NEGATED_AIRBAG_GOOD)


def drivable_state(text):
    return tri_state(text, DRIVABLE_BAD, DRIVABLE_GOOD)


def combine_states(items, state_fn):
    """Fold per-item states into one: bad wins, then good, then unknown."""
    states = {state_fn(item) for item in items if item}
    for candidate in ("bad", "good"):
        if candidate in states:
            return candidate
    return "unknown"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Fetching ─────────────────────────────────────────────────────────


def fetch(url, config, user_agent):
    """One polite GET with internal retries. Returns (status, body).

    A redirect is reported as a status rather than followed: the clean brand
    landing pages 302 to the homepage when the dealer network has no stock of
    that brand, and following it would read the homepage's mixed listings as
    that brand's stock.
    """
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    last_error = None
    for attempt in range(config["retries"] + 1):
        if attempt:
            time.sleep(config["retry_backoff_seconds"] * attempt)
        try:
            with OPENER.open(request, timeout=config["timeout_seconds"]) as response:
                body = response.read().decode("utf-8", "replace")
                return response.status, body
        except urllib.error.HTTPError as error:
            if error.code in (301, 302, 303, 307, 308):
                return error.code, ""
            last_error = error
        except Exception as error:  # noqa: BLE001 - network stack raises broadly
            last_error = error
    raise RuntimeError("GET %s failed after %d attempts: %s" % (url, config["retries"] + 1, last_error))


# ── Landing pages ────────────────────────────────────────────────────


def parse_schadeautos_cards(root):
    listings = []
    for card in find_all(root, "div", "car"):
        if "flexitem" not in classes(card):
            continue
        href = card.attrs.get("data-href") or ""
        listing_id = re.search(r"/o/(\d+)", href)
        if not listing_id:
            continue
        details = {}
        details_node = find_first(card, "div", "details")
        if details_node is not None:
            for row in find_all(details_node, "div"):
                label = (row.attrs.get("title") or "").strip()
                if label:
                    details[label] = text_of(row)
        export_node = find_first(card, "span", "label-price")
        export_price = parse_int(text_of(export_node)) if export_node is not None else None
        price, price_is_export = price_pair(parse_int(text_of(find_first(card, "div", "price"))), export_price)
        listings.append(
            {
                "id": listing_id.group(1),
                "url": SCHADEAUTOS + href,
                "title": text_of(find_first(card, "h2")),
                "trim": text_of(find_first(card, "p", "model-type")),
                "price": price,
                "price_is_export": price_is_export,
                "export_price": export_price,
                "year": parse_year(details.get("1ste toelating")),
                "km": parse_int(details.get("tellerstand")),
                "fuel": details.get("brandstof", ""),
                # Both categories render the same card markup; which landing
                # page the card came from is the only difference.
                "category": "salvage" if "/nl/schade/" in href else "clean",
            }
        )
    return listings


def parse_boonstra_cards(root):
    listings = []
    for card in find_all(root, "div", "vehicle"):
        listing_id = card.attrs.get("data-id")
        if not listing_id or "sold" in classes(card):
            continue
        link = find_first(card, "a", "image")
        if link is None:
            continue
        details = {}
        for item in find_all(card, "li"):
            spans = [child for child in item.children if isinstance(child, Node) and child.tag == "span"]
            if len(spans) >= 2:
                details[text_of(spans[0])] = text_of(spans[1])
        brand = text_of(find_first(card, "h3", "brand"))
        model = text_of(find_first(card, "div", "title"))
        listings.append(
            {
                "id": listing_id,
                "url": link.attrs.get("href", "").split("?")[0],
                "title": (brand + " " + model).strip(),
                "trim": text_of(find_first(card, "div", "edition")),
                "price": parse_int(text_of(find_first(card, "span", "price"))),
                "price_is_export": False,
                "export_price": None,
                "year": parse_year(details.get("Toelating")),
                "km": parse_int(details.get("Km stand")),
                "fuel": details.get("Brandstof", ""),
                # Boonstra lists salvage and clean stock on the same page, so
                # the category comes from the facet class, not the URL.
                "category": None,
            }
        )
    return listings


# ── Detail pages ─────────────────────────────────────────────────────


def parse_schadeautos_detail(root):
    specs = {}
    # Two rows carry damage. `schades` is the declared damage list, which also
    # states the good news when there is any ("alle airbags oké", "auto is
    # verrijdbaar", "motor loopt"); `bijzonderheden` is the dealer's free text.
    # Reading only the free text loses the damage list, which is where most
    # airbag and drivability statements actually live.
    declared = []
    free_text = []
    table = find_first(root, "div", "specifications")
    if table is not None:
        for row in find_all(table, "tr"):
            cells = [child for child in row.children if isinstance(child, Node) and child.tag == "td"]
            if len(cells) < 2:
                continue
            label = text_of(cells[0]).rstrip(":").strip().lower()
            if label == "schades":
                declared = lines_of(cells[1])
            elif label == "bijzonderheden":
                free_text = lines_of(cells[1])
            else:
                specs[label] = text_of(cells[1])
    damage_items = declared + free_text
    damage = " | ".join(
        part
        for part in (
            "Schades: " + " | ".join(declared) if declared else "",
            "Bijzonderheden: " + " | ".join(free_text) if free_text else "",
        )
        if part
    )
    return {
        "damage_text": damage,
        "damage_items": damage_items,
        "airbags": combine_states(damage_items, airbag_state),
        # No tag vocabulary here: drivable is read from the damage text alone.
        "drivable": combine_states(damage_items, drivable_state),
        "listing_price": parse_int(specs.get("verkoopprijs")),
        "export_price": parse_int(specs.get("exportprijs netto")),
        "km": parse_int(specs.get("tellerstand")),
        "year": parse_year(specs.get("1ste toelating")),
        "tags": [],
    }


def parse_boonstra_detail(root):
    page = find_first(root, "div", node_id="page")
    # The facet classes sit on the #page element itself, not on a descendant,
    # so it has to be included alongside its children.
    tokens = []
    if page is not None:
        tokens = list(classes(page))
        tokens += [token for node in walk(page) for token in classes(node)]
    tags = sorted({re.sub(r"^vehicle_tags-", "", t) for t in tokens if t.startswith("vehicle_tags-")})
    specials = {re.sub(r"^vehicle_speciaal-", "", t) for t in tokens if t.startswith("vehicle_speciaal-")}
    quarantined = any(t == "vehicle_quarantaine-y" for t in tokens)
    remarks = text_of(find_first(root, "div", "remarks-text"))

    drivable = drivable_state(remarks)
    if drivable == "unknown" and ({"rijdbaar", "verrijdbaar"} & set(tags)):
        drivable = "good"

    category = None
    if "schadevoertuig" in specials:
        category = "salvage"
    elif "occasion" in specials:
        category = "clean"

    return {
        "damage_text": remarks,
        "damage_items": [remarks] if remarks else [],
        "airbags": airbag_state(remarks),
        "drivable": drivable,
        "listing_price": None,
        "export_price": None,
        "km": None,
        "year": None,
        "tags": tags,
        "category": category,
        "quarantined": quarantined,
    }


DETAIL_PARSERS = {
    "schadeautos": parse_schadeautos_detail,
    "boonstra": parse_boonstra_detail,
}

CARD_PARSERS = {
    "schadeautos": parse_schadeautos_cards,
    "boonstra": parse_boonstra_cards,
}


# ── Filter contract ──────────────────────────────────────────────────


def match_model(listing, models):
    """Return the model a card belongs to, or None.

    Matching is on the full "brand model" phrase, never the model token alone:
    "i4" also sits inside nothing useful but "420i"/"iX1" would collide with a
    bare model token.
    """
    haystack = (listing["title"] + " " + listing["trim"]).lower()
    for model in models:
        if any(phrase in haystack for phrase in model["match"]):
            return model
    return None


def p2_variant(trim, year):
    if "dual motor" in (trim or "").lower() or re.search(r"\b(dm|awd|4wd)\b", (trim or "").lower()):
        return "dm"
    # The 2024 facelift single motor is the RWD 82 kWh car; the earlier single
    # motor is front-drive and salvage-only (EV plan decision 3).
    return "sm_facelift" if year and year >= 2024 else "sm_pre24"


def classify(listing, model, config):
    """Apply the filter contract. Returns a dict with status, route and notes.

    Absent facts do not reject. A price, mileage, year or damage field the
    platform does not state passes with an `unknown` marker so the brain can
    verify it, rather than silently dropping a car the script cannot judge.
    """
    notes = []
    damage_items = listing.get("damage_items") or [listing.get("damage_text") or ""]
    if model["key"] == "p2":
        variant = p2_variant(listing["trim"], listing["year"])
    else:
        variant = "default"

    bound = (model["bounds"].get(variant) or {}).get(listing["category"])
    route = "%s %s %s" % (model["key"], variant, listing["category"])

    if bound is None:
        reason = "route not bought (%s)" % route
        if listing["category"] == "clean":
            reason += ": salvage only"
        return {"status": "reject", "variant": variant, "route": route, "bound": None,
                "reason": reason, "notes": notes}
    if listing["year"] is None:
        notes.append("year not stated")
    elif listing["year"] < model["min_year"]:
        return {"status": "reject", "variant": variant, "route": route, "bound": bound,
                "reason": "year %d before %d" % (listing["year"], model["min_year"]), "notes": notes}
    if listing["km"] is None:
        notes.append("mileage not stated")
    elif listing["km"] > config["km_max"]:
        return {"status": "reject", "variant": variant, "route": route, "bound": bound,
                "reason": "mileage %d km over %d" % (listing["km"], config["km_max"]), "notes": notes}
    if listing.get("quarantined"):
        return {"status": "reject", "variant": variant, "route": route, "bound": bound,
                "reason": "quarantined listing", "notes": notes}
    damage_items = listing.get("damage_items") or [listing.get("damage_text") or ""]
    if "brandschade" in (listing.get("tags") or []) or any(FIRE_BAD.search(item) for item in damage_items):
        return {"status": "reject", "variant": variant, "route": route, "bound": bound,
                "reason": "fire damage", "notes": notes}
    if any(SRS_BAD.search(item) for item in damage_items):
        return {"status": "reject", "variant": variant, "route": route, "bound": bound,
                "reason": "SRS damage (pretensioners or pyro-fuse)", "notes": notes}
    if listing["airbags"] == "bad":
        return {"status": "reject", "variant": variant, "route": route, "bound": bound,
                "reason": "airbags deployed or damaged", "notes": notes}
    if listing["drivable"] == "bad":
        return {"status": "reject", "variant": variant, "route": route, "bound": bound,
                "reason": "not drivable", "notes": notes}

    if listing.get("detail_capped"):
        notes.append("damage not read (run cap on detail fetches): judge from the card only")
    if listing["airbags"] == "unknown":
        notes.append("airbags not stated: verify before committing")
    if listing["drivable"] == "unknown":
        notes.append("drivable state not stated: verify before committing")
    if listing.get("price_is_export"):
        notes.append("price is the export (net) price: the VAT-inclusive price may be higher")

    price = listing["price"]
    band = int(bound * config["near_miss_factor"])
    if price is None:
        notes.append("price not stated on the page: verify before committing")
        status = "match"
    elif price <= bound:
        status = "match"
    elif price <= band:
        status = "near_miss"
    else:
        return {"status": "reject", "variant": variant, "route": route, "bound": bound,
                "reason": "price %d over near-miss band %d" % (price, band), "notes": notes,
                # The caller uses this to decide whether the detail page is still
                # worth a fetch: the card price is a cached snapshot, so a card
                # price above the band is not proof that the listing is.
                "price_reject": True}

    return {"status": status, "variant": variant, "route": route, "bound": bound,
            "band": band, "reason": None, "notes": notes}


# ── State (the seen set) ─────────────────────────────────────────────


def load_state(path):
    if not os.path.exists(path):
        return {"version": 1, "listings": {}, "sources": {}}
    with open(path, encoding="utf-8") as handle:
        state = json.load(handle)
    state.setdefault("version", 1)
    state.setdefault("listings", {})
    state.setdefault("sources", {})
    return state


def save_state(path, state):
    state["updated"] = now_iso()
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def upsert(state, key, listing, classification, source):
    """Record a listing and report what changed since the last run."""
    now = now_iso()
    entry = state["listings"].get(key)
    change = None
    if entry is None:
        entry = {
            "key": key,
            "first_seen": now,
            "first_price": listing["price"],
            "price_history": [{"at": now, "price": listing["price"]}],
        }
        change = "new"
    else:
        previous = entry.get("last_price")
        if listing["price"] is not None and previous is not None and listing["price"] != previous:
            entry.setdefault("price_history", []).append({"at": now, "price": listing["price"]})
            if listing["price"] < previous:
                change = "price drop EUR %d to %d" % (previous, listing["price"])
            else:
                change = "price rise EUR %d to %d" % (previous, listing["price"])

    entry.update(
        {
            "source": source,
            "url": listing["url"],
            "title": listing["title"],
            "trim": listing["trim"],
            "year": listing["year"],
            "km": listing["km"],
            "fuel": listing["fuel"],
            "category": listing["category"],
            "last_price": listing["price"],
            "export_price": listing.get("export_price"),
            "price_is_export": listing.get("price_is_export", False),
            "last_seen": now,
            "status": classification["status"],
            "variant": classification["variant"],
            "route": classification["route"],
            "bound": classification["bound"],
            "reason": classification["reason"],
            "notes": classification["notes"],
            "airbags": listing["airbags"],
            "drivable": listing["drivable"],
            "damage_text": (listing["damage_text"] or "")[:1200],
            "missing_streak": 0,
        }
    )
    entry.pop("gone_at", None)
    state["listings"][key] = entry
    return entry, change


# ── Rendering ────────────────────────────────────────────────────────


def render_candidate(entry, change, model):
    price = "EUR %d" % entry["last_price"] if entry["last_price"] is not None else "not stated on the page"
    lines = [
        "[%s] %s" % ("NEAR-MISS" if entry["status"] == "near_miss" else "MATCH", entry["title"]),
        "  url: %s" % entry["url"],
        "  change: %s" % change,
        "  route: %s | bound EUR %s" % (entry["route"], entry["bound"]),
        "  price: %s" % price,
        "  year: %s | km: %s | fuel: %s" % (entry["year"], entry["km"], entry["fuel"] or "unknown"),
        "  airbags: %s | drivable: %s" % (entry["airbags"], entry["drivable"]),
        "  damage text: %s" % (entry["damage_text"] or "(none stated)"),
    ]
    if model.get("note"):
        lines.append("  rule: %s" % model["note"])
    if entry["notes"]:
        lines.append("  verify: %s" % "; ".join(entry["notes"]))
    return "\n".join(lines)


def render_run(report):
    out = [
        "EV-HUNT RUN %s" % now_iso(),
        "sources: %d/%d fetched, %d empty, %d failed"
        % (report["ok"], report["total"], report["empty"], report["failed"]),
        "listings parsed: %d | in scope: %d | matches: %d | near-misses: %d | rejected: %d"
        % (report["parsed"], report["scope"], report["matches"], report["near_misses"], report["rejected"]),
    ]
    if report["errors"]:
        out.append("source errors:")
        out.extend("  - %s" % error for error in report["errors"])
    out.append("alerts: %d" % len(report["alerts"]))
    for entry, change, model in report["alerts"]:
        out.append("")
        out.append(render_candidate(entry, change, model))
    return "\n".join(out)


def render_digest(state, config, days):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    listings = state["listings"].values()
    current = [entry for entry in listings if entry.get("missing_streak", 0) == 0]
    matches = [entry for entry in current if entry.get("status") == "match"]
    near = [entry for entry in current if entry.get("status") == "near_miss"]
    sold = [entry for entry in listings if entry.get("gone_at") and entry["gone_at"] >= cutoff_iso]
    new = [entry for entry in listings if entry.get("first_seen", "") >= cutoff_iso]

    out = [
        "EV-HUNT WEEKLY DIGEST %s" % now_iso(),
        "state: %s | seen set: %d listings (%d salvage, %d clean)"
        % (config["state_file"], len(state["listings"]),
           sum(1 for e in listings if e.get("category") == "salvage"),
           sum(1 for e in listings if e.get("category") == "clean")),
        "watched models: %s" % ", ".join(model["label"] for model in config["models"]),
        "current: %d matches, %d near-misses" % (len(matches), len(near)),
        "new in the last %d days: %d" % (days, len(new)),
    ]

    price_changes = []
    for entry in listings:
        # Index 0 is the price the listing was first seen at, not a change.
        for change in entry.get("price_history", [])[1:]:
            if change["at"] >= cutoff_iso:
                price_changes.append((entry, change))
    out.append("price changes in the last %d days: %d" % (days, len(price_changes)))
    for entry, change in price_changes:
        out.append("  - %s changed %s to EUR %s" % (entry["title"], change["at"][:10], change["price"]))

    out.append("no longer seen (%d):" % len(sold))
    for entry in sold:
        out.append(
            "  - %s | last seen %s | last price EUR %s | %s"
            % (entry["title"], entry.get("last_seen", "?")[:10], entry.get("last_price"), entry["url"])
        )

    out.append("near-miss inventory (%d):" % len(near))
    for entry in near:
        delta = (entry.get("last_price") or 0) - (entry.get("bound") or 0)
        relation = "EUR %d over bound" % delta if delta >= 0 else "EUR %d under bound" % -delta
        out.append("  - EUR %s (%s) | %s" % (entry.get("last_price"), relation, entry["url"]))

    out.append("matches (%d):" % len(matches))
    for entry in matches:
        out.append(
            "  - EUR %s under bound EUR %s | %s | %s"
            % ((entry.get("bound") or 0) - (entry.get("last_price") or 0), entry.get("bound"),
               entry["title"], entry["url"])
        )
    if matches:
        prices = sorted(entry["last_price"] for entry in matches if entry.get("last_price"))
        if prices:
            out.append("week-4 review data point: median match price EUR %d across %d matches" % (prices[len(prices) // 2], len(prices)))
    return "\n".join(out)


# ── Run ──────────────────────────────────────────────────────────────


def run(config, state):
    report = {
        "total": len(config["sources"]), "ok": 0, "empty": 0, "failed": 0,
        "parsed": 0, "scope": 0, "matches": 0, "near_misses": 0, "rejected": 0,
        "alerts": [], "errors": [],
    }
    succeeded_sources = set()
    seen_keys = set()
    hard_failures = []
    detail_fetches = 0
    user_agent = config["user_agent"]

    for source in config["sources"]:
        name = source["name"]
        previous = state["sources"].get(name, {})
        try:
            status, body = fetch(source["url"], config, user_agent)
        except RuntimeError as error:
            report["failed"] += 1
            report["errors"].append("%s: %s" % (name, error))
            state["sources"][name] = {"last_count": previous.get("last_count", 0), "last_ok": False, "last_run": now_iso()}
            continue

        if status in (301, 302, 303, 307, 308) or status >= 400:
            # No stock: the clean brand landing pages redirect to the homepage
            # when the network carries none of that brand. That is an empty
            # result, not a failure, and not structural drift either.
            report["empty"] += 1
            state["sources"][name] = {"last_count": 0, "last_ok": True, "last_run": now_iso()}
            succeeded_sources.add(name)
            continue

        cards = CARD_PARSERS[source["platform"]](parse_html(body))
        # Boonstra renders salvage and clean stock in one list, so its card
        # parser cannot tell the category; the filtered landing page it came
        # from is the answer until the detail page says otherwise.
        for card in cards:
            if not card["category"]:
                card["category"] = source["category"]
        report["parsed"] += len(cards)
        report["ok"] += 1
        succeeded_sources.add(name)

        if not cards and previous.get("last_count", 0) > 0:
            # The page parsed cards last run and none now. Reading that as "no
            # news" would hide a markup change, so it fails loudly instead.
            hard_failures.append("%s: page yielded no listings but yielded %d last run" % (name, previous["last_count"]))
        state["sources"][name] = {"last_count": len(cards), "last_ok": True, "last_run": now_iso()}

        if config["request_delay_seconds"]:
            time.sleep(config["request_delay_seconds"])

        for card in cards:
            model = match_model(card, config["models"])
            if model is None:
                continue
            report["scope"] += 1
            listing = dict(card)
            listing["airbags"] = "unknown"
            listing["drivable"] = "unknown"
            listing["damage_text"] = ""
            listing["damage_items"] = []
            listing["tags"] = []
            listing.setdefault("price_is_export", False)
            key = "%s:%s" % (source["platform"], card["id"])

            # Only listings the card can rule out are skipped: it states model,
            # year and mileage reliably, but its price is a cached snapshot and
            # it states no damage at all. Anything else gets a detail fetch.
            provisional = classify(listing, model, config)
            if provisional["status"] != "reject" or provisional.get("price_reject"):
                if detail_fetches < config["max_detail_fetches"]:
                    detail_fetches += 1
                    detail = fetch_detail(card["url"], source["platform"], config, user_agent)
                    for field in ("airbags", "drivable", "damage_text", "damage_items", "tags"):
                        if detail.get(field) is not None:
                            listing[field] = detail[field]
                    if detail.get("listing_price"):
                        listing["price"] = detail["listing_price"]
                        listing["price_is_export"] = False
                    elif detail.get("export_price") and listing["price"] is None:
                        listing["price"] = detail["export_price"]
                        listing["price_is_export"] = True
                    if detail.get("export_price"):
                        listing["export_price"] = detail["export_price"]
                    if detail.get("category"):
                        listing["category"] = detail["category"]
                    if detail.get("km"):
                        listing["km"] = detail["km"]
                    if detail.get("year"):
                        listing["year"] = detail["year"]
                    if config["request_delay_seconds"]:
                        time.sleep(config["request_delay_seconds"])
                else:
                    listing["detail_capped"] = True

            classification = classify(listing, model, config)
            entry, change = upsert(state, key, listing, classification, name)
            seen_keys.add(key)

            if classification["status"] == "reject":
                report["rejected"] += 1
            elif classification["status"] == "match":
                report["matches"] += 1
                if change:
                    report["alerts"].append((entry, change, model))
            else:
                report["near_misses"] += 1
                if change:
                    report["alerts"].append((entry, change, model))

    # A listing absent from a source that succeeded this run is a candidate for
    # "gone". Sources that failed (or were empty) are skipped so a network blip
    # does not look like a sale.
    for key, entry in state["listings"].items():
        if key in seen_keys or entry.get("source") not in succeeded_sources:
            continue
        entry["missing_streak"] = entry.get("missing_streak", 0) + 1
        if entry["missing_streak"] >= config["missing_runs_before_gone"] and not entry.get("gone_at"):
            entry["gone_at"] = now_iso()

    if hard_failures:
        raise RuntimeError("; ".join(hard_failures))
    if report["ok"] == 0 and report["empty"] == 0:
        raise RuntimeError("no landing page could be fetched")
    return report


def fetch_detail(url, platform, config, user_agent):
    try:
        status, body = fetch(url, config, user_agent)
    except RuntimeError:
        return {}
    if status != 200:
        return {}
    return DETAIL_PARSERS[platform](parse_html(body))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=None, help="filter-contract JSON (default: alongside this script)")
    parser.add_argument("--state", default=None, help="override the state file path from the config")
    parser.add_argument("--digest", action="store_true", help="print the weekly digest from state instead of fetching")
    parser.add_argument("--digest-days", type=int, default=7, help="window for the digest (default: 7)")
    args = parser.parse_args(argv)

    config_path = args.config or os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    try:
        with open(config_path, encoding="utf-8") as handle:
            config = json.load(handle)
        if args.state:
            config["state_file"] = args.state
        state = load_state(config["state_file"])
    except (OSError, ValueError) as error:
        print("EV-HUNT FAILED %s" % now_iso())
        print("error: cannot read the config or the state file: %s" % error)
        return 1

    if args.digest:
        print(render_digest(state, config, args.digest_days))
        return 0

    try:
        report = run(config, state)
    except RuntimeError as error:
        # Non-zero exit is the contract with the skill: the brain may fall back
        # to its own web tools and mark the run degraded.
        print("EV-HUNT FAILED %s" % now_iso())
        print("error: %s" % error)
        return 1

    save_state(config["state_file"], state)
    print(render_run(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
