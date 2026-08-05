"""Investigate why Nhom A metrics are low (results/*/summary.json).

Reads per_query.json + gen_user_data/data/listings.json (derived from
Data/Final_Data.csv) to check two hypotheses:

1. filters_applied.district (hard filter sent to the live system) does not
   match the district(s) relevance_v2() actually accepted when building
   ground truth (users can have multiple preferred_districts; the hard
   filter is one random pick from that set — see gen_v2.py:249,271).
2. Ground truth itself is drawn from a random 500-listing pool per event
   (gen_v2.py:252-255), not the full 3030 catalog, so a live system
   searching the full catalog can legitimately find better, unseen items.

    cd Evaluation && python investigate_low_scores.py results/<run_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import config as C


def main():
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if run_dir is None:
        candidates = sorted(C.RESULTS_DIR.glob("*_n*"), key=lambda p: p.name)
        if not candidates:
            print("No results/*_n* run folder found.")
            return
        run_dir = candidates[-1]
    per_query = json.load(open(run_dir / "per_query.json", encoding="utf-8"))
    listings = {l["listing_id"]: l for l in json.load(open(C.LISTINGS_FILE, encoding="utf-8"))}
    users = json.load(open(C.USERS_FILE, encoding="utf-8"))
    users_by_id = {u["user_id"]: u for u in users}

    print(f"[investigate] run: {run_dir.name}, {len(per_query)} queries\n")

    # --- Hypothesis 1: filters_applied.district vs ground_truth's actual districts ---
    n_with_district_filter = 0
    n_gt_matches_filter_district = 0  # ALL 10 ground truth items are in filters_applied district
    n_gt_partial_match = 0            # SOME but not all
    n_gt_zero_match = 0               # NONE of the 10 ground truth items are in filters_applied district
    n_user_multi_district = 0

    examples_zero_match = []

    for row in per_query:
        filt = row.get("filters_applied") or {}
        filt_district = filt.get("district")
        if not filt_district:
            continue
        n_with_district_filter += 1

        user = users_by_id.get(row.get("user_id"))
        if user:
            pref_districts = {d["value"] for d in user["explicit_preferences"]["preferred_districts"]}
            if len(pref_districts) > 1:
                n_user_multi_district += 1

        gt_districts = [listings[g["listing_id"]]["district"] for g in row["ground_truth"]
                         if g["listing_id"] in listings]
        n_match = sum(1 for d in gt_districts if d == filt_district)
        if n_match == len(gt_districts):
            n_gt_matches_filter_district += 1
        elif n_match == 0:
            n_gt_zero_match += 1
            if len(examples_zero_match) < 5:
                examples_zero_match.append((row, filt_district, gt_districts))
        else:
            n_gt_partial_match += 1

    print("=== Gia thuyet 1: filters_applied.district vs district that cua ground truth ===")
    print(f"Events co filters_applied.district: {n_with_district_filter}/{len(per_query)}")
    print(f"  -> user co NHIEU preferred_districts (co the gay lech): {n_user_multi_district}")
    print(f"  -> CA 10 ground truth item DUNG quan filter: {n_gt_matches_filter_district}")
    print(f"  -> MOT PHAN ground truth item dung quan filter: {n_gt_partial_match}")
    print(f"  -> KHONG CO item ground truth nao dung quan filter (0/10): {n_gt_zero_match}")

    if examples_zero_match:
        print("\n--- Vi du events ma TOAN BO ground truth KHONG nam trong filters_applied.district ---")
        for row, filt_d, gt_ds in examples_zero_match:
            print(f"\nresult_set_id={row['result_set_id']}  user_id={row['user_id']}")
            print(f"  raw_query: {row['raw_query']}")
            print(f"  filters_applied: {row['filters_applied']}  (filter district = {filt_d!r})")
            print(f"  ground_truth districts thuc te: {gt_ds}")
            print(f"  n_hits (live pred trung ground truth): {row['n_hits']}")

    # --- Hypothesis 2: does live_pred even respect filters_applied.district? ---
    print("\n=== Gia thuyet 1b: he thong that co tra ve dung quan filter khong? ===")
    n_pred_checked = 0
    n_pred_all_match = 0
    for row in per_query:
        filt = row.get("filters_applied") or {}
        filt_district = filt.get("district")
        if not filt_district or not row["live_pred"]:
            continue
        n_pred_checked += 1
        pred_districts = [listings[p["listing_id"]]["district"] for p in row["live_pred"]
                           if p["listing_id"] in listings]
        if pred_districts and all(d == filt_district for d in pred_districts):
            n_pred_all_match += 1
    print(f"Events co live_pred + filter district: {n_pred_checked}")
    print(f"  -> live_pred TOAN BO dung quan filter (he thong ap dung filter dung): {n_pred_all_match}")

    # --- Show one concrete example end-to-end for manual inspection ---
    print("\n=== Vi du chi tiet 1 query (so sanh truc tiep) ===")
    row = per_query[0]
    print(f"raw_query: {row['raw_query']}")
    print(f"filters_applied: {row['filters_applied']}")
    print("\nGround truth (top 3/10):")
    for g in row["ground_truth"][:3]:
        l = listings.get(g["listing_id"], {})
        print(f"  id={g['listing_id']} rank={g['rank']} score={g['score']:.3f} "
              f"district={l.get('district')} price={l.get('price_billion')} "
              f"beds={l.get('bedrooms')} type={l.get('property_type')}")
    print("\nLive pred (top 3/10):")
    for p in row["live_pred"][:3]:
        l = listings.get(p["listing_id"], {})
        print(f"  id={p['listing_id']} rank={p['rank']} score={p['score']:.3f} "
              f"district={l.get('district')} price={l.get('price_billion')} "
              f"beds={l.get('bedrooms')} type={l.get('property_type')}")


if __name__ == "__main__":
    main()
