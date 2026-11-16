"""Fetch trends yourself (e.g. on your home PC) and optionally push them to the live site.

  python refresh.py
  python refresh.py --push https://your-app.onrender.com --token YOUR_ADMIN_TOKEN
"""
import argparse
import logging

import requests

import database as db
import trends
from keywords import CATEGORIES, GEOS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
p = argparse.ArgumentParser()
p.add_argument("--push")
p.add_argument("--token", default="")
args = p.parse_args()

db.initialize_database()
print("Finished all regions" if trends.refresh_all() else "Stopped early (rate limited) - run again later")

if args.push:
    body = {g: {c: {r["name"]: r["score"] for r in db.get_scores(g, c)} for c in CATEGORIES} for g in GEOS}
    r = requests.post(args.push.rstrip("/") + "/api/import", json=body,
                      headers={"X-Admin-Token": args.token}, timeout=60)
    print("Push:", r.status_code, r.text)
