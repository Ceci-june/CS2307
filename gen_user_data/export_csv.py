"""Xuất các dataset JSON sang CSV (phẳng, dễ mở bằng Excel/BI).

    cd gen_user_data && python export_csv.py

Đầu ra -> data/csv/:
  users.csv         : mỗi user 1 dòng; list -> chuỗi nối bằng '|'
  listings.csv      : mỗi listing 1 dòng; 25 cột feature boolean tách riêng
  interactions.csv  : mỗi event 1 dòng; context.* phẳng
  eval_results.csv  : mỗi recommender 1 dòng; metric là cột
"""
from __future__ import annotations

import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
CSV_DIR = os.path.join(DATA_DIR, "csv")
KG_DIR = os.path.join(DATA_DIR, "kg")
PC_DIR = os.path.join(DATA_DIR, "precomputed")


def _read(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def _read_path(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _join(v):
    return "|".join(map(str, v)) if isinstance(v, list) else v


def export_users() -> pd.DataFrame:
    rows = []
    for u in _read("users.json"):
        d, p = u["demographics"], u["explicit_preferences"]
        rows.append({
            "user_id": u["user_id"], "segment": u["segment"],
            "primary_intent": u["primary_intent"],
            "age_group": d["age_group"], "marital_status": d["marital_status"],
            "children": d["children"], "income_level": d["income_level"],
            "preferred_districts": _join(p["preferred_districts"]),
            "min_bedrooms": p["min_bedrooms"],
            "budget_min": p["budget_range"][0], "budget_max": p["budget_range"][1],
            "property_type": _join(p["property_type"]),
            "liked_amenities": _join(p["liked_amenities"]),
        })
    return pd.DataFrame(rows)


def export_listings() -> pd.DataFrame:
    rows = []
    for l in _read("listings.json"):
        row = {k: v for k, v in l.items() if k != "features"}
        row.update(l["features"])  # tách 25 cột boolean
        rows.append(row)
    return pd.DataFrame(rows)


def export_interactions() -> pd.DataFrame:
    rows = []
    for it in _read("interactions.json"):
        c = it["context"]
        f = c.get("filters_applied", {})
        rows.append({
            "interaction_id": it["interaction_id"], "user_id": it["user_id"],
            "session_id": it["session_id"], "listing_id": it["listing_id"],
            "action_type": it["action_type"], "timestamp": it["timestamp"],
            "dwell_time_seconds": it["dwell_time_seconds"], "source": it["source"],
            "implicit_score": it["implicit_score"], "is_bounce": it["is_bounce"],
            "raw_query": c["raw_query"], "inferred_intent": c["inferred_intent"],
            "budget_group": c["budget_group"],
            "filter_price_max": f.get("price_max"), "filter_bedrooms": f.get("bedrooms"),
        })
    return pd.DataFrame(rows)


def export_eval() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "eval_results.json")
    if not os.path.exists(path):
        print("[csv] eval_results.json chưa có (chạy run_eval.py trước) — bỏ qua.")
        return pd.DataFrame()
    blob = _read("eval_results.json")
    rows = []
    for name, metrics in blob["results"].items():
        row = {"recommender": name, "k": blob.get("k"),
               "num_neg_samples": blob.get("num_neg_samples")}
        row.update({m: v for m, v in metrics.items() if m != "engine"})
        row["engine"] = metrics.get("engine")
        rows.append(row)
    return pd.DataFrame(rows)


# --- Similarity edges (declared + location) ---------------------------------
def export_similarity_edges() -> pd.DataFrame:
    rows = []
    for fname in ("similarity_edges.json", "location_similarity_edges.json"):
        path = os.path.join(KG_DIR, fname)
        if os.path.exists(path):
            rows += _read_path(path)
    return pd.DataFrame(rows)


# --- Precomputed artifacts (nếu đã chạy precompute.py) ----------------------
def export_content_neighbors() -> pd.DataFrame:
    path = os.path.join(PC_DIR, "content_neighbors.json")
    if not os.path.exists(path):
        return pd.DataFrame()
    rows = [{"listing_id": int(lid), "rank": r, "neighbor_id": n["listing_id"], "sim": n["sim"]}
            for lid, nbrs in _read_path(path).items() for r, n in enumerate(nbrs)]
    return pd.DataFrame(rows)


def export_co_engagement() -> pd.DataFrame:
    path = os.path.join(PC_DIR, "co_engagement.json")
    if not os.path.exists(path):
        return pd.DataFrame()
    rows = [{"listing_id": int(lid), "rank": r, "neighbor_id": n["listing_id"], "score": n["score"]}
            for lid, nbrs in _read_path(path).items() for r, n in enumerate(nbrs)]
    return pd.DataFrame(rows)


def export_popularity() -> pd.DataFrame:
    path = os.path.join(PC_DIR, "popularity.json")
    if not os.path.exists(path):
        return pd.DataFrame()
    per = _read_path(path).get("per_listing", {})
    return pd.DataFrame([{"listing_id": int(k), "popularity": v} for k, v in per.items()])


def export_query_expansion() -> pd.DataFrame:
    path = os.path.join(PC_DIR, "query_expansion.json")
    if not os.path.exists(path):
        return pd.DataFrame()
    rows = [{"attr": a, "related": e["attr"], "weight": e["weight"], "group": e["group"]}
            for a, exps in _read_path(path).items() for e in exps]
    return pd.DataFrame(rows)


def export_segment_affinity() -> pd.DataFrame:
    path = os.path.join(PC_DIR, "segment_affinity.json")
    if not os.path.exists(path):
        return pd.DataFrame()
    rows = [{"segment_intent": k, "amenity": e["amenity"], "affinity": e["affinity"]}
            for k, items in _read_path(path).items() for e in items]
    return pd.DataFrame(rows)


def main():
    os.makedirs(CSV_DIR, exist_ok=True)
    # (tên file, hàm, bắt buộc?) — không bắt buộc thì thiếu nguồn sẽ bỏ qua
    exporters = [
        ("users.csv", export_users, True),
        ("listings.csv", export_listings, True),
        ("interactions.csv", export_interactions, True),
        ("eval_results.csv", export_eval, False),
        ("similarity_edges.csv", export_similarity_edges, False),
        ("content_neighbors.csv", export_content_neighbors, False),
        ("co_engagement.csv", export_co_engagement, False),
        ("popularity.csv", export_popularity, False),
        ("query_expansion.csv", export_query_expansion, False),
        ("segment_affinity.csv", export_segment_affinity, False),
    ]
    for fname, fn, required in exporters:
        df = fn()
        if df.empty and not required:
            print(f"[csv] {fname:<24} (bỏ qua — chưa có nguồn)")
            continue
        out = os.path.join(CSV_DIR, fname)
        df.to_csv(out, index=False, encoding="utf-8-sig")  # utf-8-sig để Excel đọc tiếng Việt
        print(f"[csv] {fname:<24} {len(df):>6} rows x {len(df.columns):>2} cols -> {out}")


if __name__ == "__main__":
    main()
