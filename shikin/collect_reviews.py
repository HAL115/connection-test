#!/usr/bin/env python3
"""Googleマップの口コミ集計（評価・件数）を会社ごとに集める。

Places API (New) の Text Search を読み取り専用サービスアカウントで叩く。
前提：プロジェクトで Places API (New) が有効になっていること。
住所の照合：既知の所在地（profiles.json）と検索結果の住所で、都道府県と市区町村が
一致したものだけを採用する。一致しないものは 'unmatched' として記録し、表示しない。

出力: reviews.json {entity_id: {rating, count, place_name, address, checked}}
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.expanduser(
    "~/workspace/custom-connectors/custom.google-analytics/.venv/lib/python3.12/site-packages"))
from google.oauth2 import service_account  # noqa: E402
from google.auth.transport.requests import Request as AuthRequest  # noqa: E402
import requests  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = "/home/hatch/.config/muse/google/service-account.json"
CHECKED = "2026-11-24"


def city_key(addr):
    if not addr:
        return ""
    m = re.search(r"(東京都|北海道|(?:京都|大阪)府|.{2,3}県)(.{2,8}?[市区町村])", addr)
    return (m.group(1) + m.group(2)) if m else addr[:8]


def main():
    data = json.load(open(os.path.join(HERE, "data.json")))
    profiles = {}
    try:
        profiles = json.load(open(os.path.join(HERE, "profiles.json")))
    except Exception:
        pass
    out_path = os.path.join(HERE, "reviews.json")
    out = {}
    if os.path.exists(out_path):
        out = json.load(open(out_path))

    creds = service_account.Credentials.from_service_account_file(
        KEY, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(AuthRequest())
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "X-Goog-FieldMask": "places.id,places.displayName,places.rating,places.userRatingCount,places.formattedAddress",
        "Content-Type": "application/json",
    }

    ents = data["entities"]
    done = matched = 0
    for e in ents:
        eid = e["id"]
        if eid in out:
            continue
        prof = profiles.get(eid, {})
        addr = prof.get("location") or e.get("location") or ""
        name = e["name"]
        q = f"{name} {addr}".strip()
        try:
            r = requests.post(
                "https://places.googleapis.com/v1/places:searchText",
                headers=headers,
                json={"textQuery": q, "languageCode": "ja", "regionCode": "JP", "maxResultCount": 3},
                timeout=30)
        except Exception as ex:
            print(eid, "request error", ex)
            continue
        if r.status_code == 429:
            print("rate limited; stopping")
            break
        if r.status_code != 200:
            print(eid, "status", r.status_code, r.text[:200])
            if r.status_code == 403:
                print("Places API が有効でない可能性があります。中止します。")
                break
            continue
        places = r.json().get("places", [])
        rec = None
        for p in places:
            paddr = p.get("formattedAddress", "")
            if city_key(addr) and city_key(paddr) and city_key(addr) == city_key(paddr):
                rec = p
                break
        if rec is None and places and not addr:
            rec = places[0]
        if rec and rec.get("userRatingCount"):
            out[eid] = {
                "rating": rec.get("rating"),
                "count": rec.get("userRatingCount"),
                "place_name": rec.get("displayName", {}).get("text", ""),
                "address": rec.get("formattedAddress", ""),
                "checked": CHECKED,
            }
            matched += 1
        else:
            out[eid] = {"count": 0, "checked": CHECKED, "unmatched": True}
        done += 1
        if done % 25 == 0:
            json.dump(out, open(out_path, "w"), ensure_ascii=False, indent=1)
            print(f"progress {done}/{len(ents)} matched={matched}", flush=True)
        time.sleep(0.15)
    json.dump(out, open(out_path, "w"), ensure_ascii=False, indent=1)
    print(f"done {done} matched={matched} total_records={len(out)}")


if __name__ == "__main__":
    main()
