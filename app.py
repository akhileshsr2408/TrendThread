import hmac
import json
import logging
import os
import threading
import time

from flask import Flask, jsonify, render_template, request

import database as db
import trends
from keywords import CATEGORIES, GEOS, REGIONS, SOUTH_LABEL
import database as d,time
b=float(d.get_meta('refresh_blocked_until',0) or 0)
print('blocked for another', max(0,round((b-time.time())/60)), 'min')
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("trendthread")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
REFRESH_HOURS = float(os.environ.get("REFRESH_HOURS", "24"))
DEFAULT_LIMIT, MAX_LIMIT = 5, 20
_lock = threading.Lock()

db.initialize_database()


# ---------- scores ----------
def current_scores(geo, category):
    """{Name: ratio} for one geo, limited to names still on the keyword list."""
    allowed = {n.title() for n in CATEGORIES[category]["names"]}
    return {r["name"]: r["score"] for r in db.get_scores(geo, category) if r["name"] in allowed}


def geo_coverage(geo, category):
    return len(current_scores(geo, category)) / len(CATEGORIES[category]["names"])


def is_complete():
    return all(geo_coverage(g, c) >= 0.8 for g in GEOS for c in CATEGORIES)


def mean_merge(dicts):
    acc = {}
    for d in dicts:
        for k, v in d.items():
            acc.setdefault(k, []).append(v)
    return {k: sum(v) / len(v) for k, v in acc.items()}


def region_scores(region, category):
    """Average over the region's geos that have enough data (>=50% collected)."""
    geos = [g for g in REGIONS[region][1] if geo_coverage(g, category) >= 0.5]
    return mean_merge([current_scores(g, category) for g in geos])


def area_scores(area, category):
    """Returns (scores, labels of regions that contributed). area = 'south' or a region key."""
    if area == "south":
        parts = {r: region_scores(r, category) for r in REGIONS}
        used = [REGIONS[r][0] for r, p in parts.items() if p]
        return mean_merge([p for p in parts.values() if p]), used
    scores = region_scores(area, category)
    return scores, ([REGIONS[area][0]] if scores else [])


def top_list(scores, limit):
    if not scores:
        return None
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best = ranked[0][1] or 1
    return [{"name": n, "score": round(s / best * 100)} for n, s in ranked[:limit]]


# ---------- background refresh ----------
def _is_running():
    started = float(db.get_meta("refresh_started", 0) or 0)
    return db.get_meta("refresh_running") == "1" and time.time() - started < 3 * 3600


def _worker():
    try:
        finished_ok = trends.refresh_all()
        if is_complete():
            db.set_meta("refresh_finished", time.time())
        elif not finished_ok:
            # Google rate-limited us: stay away for 45 minutes so the block can expire
            db.set_meta("refresh_blocked_until", time.time() + 45 * 60)
    except Exception:
        log.exception("Refresh crashed")
    finally:
        db.set_meta("refresh_running", "0")


def start_refresh():
    with _lock:
        if _is_running():
            return False
        db.set_meta("refresh_running", "1")
        db.set_meta("refresh_started", time.time())
        threading.Thread(target=_worker, daemon=True).start()
        return True


def is_stale():
    if not is_complete():
        # Partial data: retry, but not while rate-limited, and not more often than every 5 minutes
        now = time.time()
        return (now >= float(db.get_meta("refresh_blocked_until", 0) or 0)
                and now - float(db.get_meta("refresh_started", 0) or 0) > 5 * 60)
    return time.time() - float(db.get_meta("refresh_finished", 0) or 0) > REFRESH_HOURS * 3600


def maybe_refresh():
    if is_stale():
        start_refresh()


def admin_ok():
    sent = request.headers.get("X-Admin-Token", "")
    return bool(ADMIN_TOKEN) and hmac.compare_digest(sent, ADMIN_TOKEN)


# A freshly started process has no refresh thread running, so clear the leftover flag.
db.set_meta("refresh_running", "0")


# ---------- routes ----------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return "ok"


@app.route("/api/trends/<category>")
def get_trends(category):
    if category not in CATEGORIES and category != "both":
        return jsonify(success=False, message="Invalid category"), 400
    region = request.args.get("region", "south")
    if region != "south" and region not in REGIONS:
        return jsonify(success=False, message="Invalid region"), 400
    try:
        limit = max(1, min(int(request.args.get("limit", DEFAULT_LIMIT)), MAX_LIMIT))
    except ValueError:
        limit = DEFAULT_LIMIT

    maybe_refresh()
    cats = list(CATEGORIES) if category == "both" else [category]
    data, used = {}, {}
    for c in cats:
        scores, used[c] = area_scores(region, c)
        data[c] = top_list(scores, limit)

    if any(v is None for v in data.values()):
        done = sum(len(current_scores(g, c)) for g in GEOS for c in cats)
        total = len(GEOS) * sum(len(CATEGORIES[c]["names"]) for c in cats)
        return jsonify(success=False, refreshing=_is_running(),
                       message=f"Still collecting trend data from Google ({done} of {total} data points "
                               "so far). This takes several minutes - please check back shortly."), 503

    db.add_history(category)
    label = SOUTH_LABEL if region == "south" else REGIONS[region][0]
    included = used[cats[0]]
    payload = {"success": True, "category": "Both" if category == "both" else CATEGORIES[category]["label"],
               "region": label, "regions_included": included,
               "partial": region == "south" and len(included) < len(REGIONS),
               "limit": limit, "updated_at": max(db.last_updated(c) or "" for c in cats),
               "refreshing": _is_running()}
    if category == "both":
        payload.update(colors=data["colors"], fabrics=data["fabrics"])
    else:
        payload["results"] = data[category]
    return jsonify(payload)


@app.route("/api/status")
def status():
    return jsonify(refreshing=_is_running(), stale=is_stale(), complete=is_complete(),
                   tracked={g: {c: len(current_scores(g, c)) for c in CATEGORIES} for g in GEOS})


@app.route("/api/refresh", methods=["POST"])
def refresh():
    if not admin_ok():
        return jsonify(success=False, message="Forbidden"), 403
    return jsonify(success=True, started=start_refresh())


@app.route("/api/import", methods=["POST"])
def import_scores():
    """Accepts {"IN-TN": {"colors": {"Black": 1.2}, "fabrics": {...}}, ...} (see refresh.py --push)."""
    if not admin_ok():
        return jsonify(success=False, message="Forbidden"), 403
    body = request.get_json(silent=True) or {}
    count = 0
    for geo, cats in body.items():
        if geo not in GEOS or not isinstance(cats, dict):
            continue
        for cat, scores in cats.items():
            if cat not in CATEGORIES or not isinstance(scores, dict):
                continue
            clean = {str(k)[:60]: float(v) for k, v in scores.items() if isinstance(v, (int, float))}
            db.upsert_scores(geo, cat, clean)
            count += len(clean)
    if count and is_complete():
        db.set_meta("refresh_finished", time.time())
    return jsonify(success=True, imported=count)


@app.route("/api/history")
def history():
    return jsonify(db.get_history())


@app.route("/api/save", methods=["POST"])
def save_current_trend():
    data = request.get_json(silent=True) or {}
    category, results = str(data.get("category", "")).lower(), data.get("results")
    if category not in (*CATEGORIES, "both") or not isinstance(results, (list, dict)):
        return jsonify(success=False, message="Invalid trend data"), 400
    db.save_trend(category, json.dumps(results))
    return jsonify(success=True, message="Trend saved successfully")


@app.route("/api/saved")
def saved():
    return jsonify(db.get_saved_trends())


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1",
            port=int(os.environ.get("PORT", 5000)))
