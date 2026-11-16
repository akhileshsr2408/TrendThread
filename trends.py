"""Fetches Google Trends per region for many keywords, using an anchor term per batch."""
import logging
import os
import random
import time

from pytrends.request import TrendReq

import database as db
from keywords import CATEGORIES, GEOS, term

log = logging.getLogger("trendthread")
BATCH_SIZE = 4                       # + 1 anchor = Google's 5-keyword limit
TIMEFRAME = os.environ.get("TRENDS_TIMEFRAME", "today 3-m")
RESUME_HOURS = min(12, float(os.environ.get("REFRESH_HOURS", "24")) / 2)


def fetch_batch(anchor, names, geo):
    """Return {Name: ratio-to-anchor} for up to 4 names in one region."""
    terms = {term(n): n for n in names}
    anchor_term = term(anchor)
    # retries/backoff are handled in refresh_category; pytrends' own retry option
    # crashes on urllib3 2.x ("method_whitelist"), so it is left off.
    py = TrendReq(hl="en-US", tz=330, timeout=(10, 30))
    py.build_payload([anchor_term] + list(terms), timeframe=TIMEFRAME, geo=geo)
    df = py.interest_over_time()
    if df.empty or anchor_term not in df.columns:
        return {}
    anchor_mean = float(df[anchor_term].mean())
    if anchor_mean == 0:
        log.warning("%s: anchor had zero interest for batch %s; skipped", geo, names)
        return {}
    return {
        n.title(): float(df[t].mean()) / anchor_mean
        for t, n in terms.items() if t in df.columns
    }


def refresh_category(geo, category, pause=(35, 60)):
    """Fetch every keyword for one region+category. Returns True if finished, False if rate-limited."""
    cfg = CATEGORIES[category]
    anchor = cfg["anchor"]
    db.upsert_scores(geo, category, {anchor.title(): 1.0})   # the anchor is the 1.0 baseline

    # Resume: skip names fetched recently, so a retry after a rate limit continues where it stopped
    fresh = db.fresh_names(geo, category, RESUME_HOURS)
    names = [n for n in cfg["names"] if n != anchor and n.title() not in fresh]

    for i in range(0, len(names), BATCH_SIZE):
        batch = names[i:i + BATCH_SIZE]
        for attempt in (1, 2):
            try:
                db.upsert_scores(geo, category, fetch_batch(anchor, batch, geo))
                log.info("%s %s batch %s ok", geo, category, batch)
                break
            except Exception as e:                      # usually a 429 rate limit
                log.warning("%s %s batch %s failed (%s): %r", geo, category, batch, attempt, e)
                if attempt == 2:
                    log.error("Giving up for now (likely rate-limited); will resume later.")
                    return False
                time.sleep(60)
        time.sleep(random.uniform(*pause))
    return True


def refresh_all():
    """Region by region, so finished regions are usable even if Google blocks us midway."""
    for geo in GEOS:
        for category in CATEGORIES:
            if not refresh_category(geo, category):
                return False
    return True
