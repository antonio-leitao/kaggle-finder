#!/usr/bin/env python3
"""Build static/data/competitions.json from a Meta Kaggle dump.

Reads three CSVs from --csv-dir (Tags.csv, Competitions.csv, CompetitionTags.csv),
filters to finalized competitions, keeps only the tags we surface in the UI,
and writes one JSON bundle to --out.

Run on a cron via .github/workflows/refresh.yml.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# The taxonomy the UI knows about. Anything not in here is dropped from the
# build. Slugs match Meta Kaggle's `tags.Slug` column directly. Names are what
# the UI shows on chips and result tags.
TAXONOMY: dict[str, dict[str, str]] = {
    # data
    "tabular":                    {"name": "tabular",                    "group": "data"},
    "time-series":                {"name": "time series",                "group": "data"},
    "image-data":                 {"name": "image data",                 "group": "data"},
    "text-data":                  {"name": "text data",                  "group": "data"},
    "audio-data":                 {"name": "audio data",                 "group": "data"},
    "video":                      {"name": "video",                      "group": "data"},
    "sequential":                 {"name": "sequential",                 "group": "data"},
    # task
    "binary-classification":      {"name": "binary classification",      "group": "task"},
    "multiclass-classification":  {"name": "multiclass classification",  "group": "task"},
    "multilabel-classification":  {"name": "multilabel classification",  "group": "task"},
    "regression":                 {"name": "regression",                 "group": "task"},
    "forecasting":                {"name": "forecasting",                "group": "task"},
    "anomaly-detection":          {"name": "anomaly detection",          "group": "task"},
    "object-detection":           {"name": "object detection",           "group": "task"},
    "semantic-segmentation":      {"name": "semantic segmentation",      "group": "task"},
    "ranking":                    {"name": "ranking",                    "group": "task"},
    "nlp":                        {"name": "nlp",                        "group": "task"},
    "computer-vision":            {"name": "computer vision",            "group": "task"},
    # domain
    "healthcare":                 {"name": "healthcare",                 "group": "domain"},
    "finance":                    {"name": "finance",                    "group": "domain"},
    "biology":                    {"name": "biology",                    "group": "domain"},
    "physics":                    {"name": "physics",                    "group": "domain"},
    "earth-and-nature":           {"name": "earth and nature",           "group": "domain"},
    "manufacturing":              {"name": "manufacturing",              "group": "domain"},
    "automobile":                 {"name": "automobile",                 "group": "domain"},
    "internet":                   {"name": "internet",                   "group": "domain"},
    "education":                  {"name": "education",                  "group": "domain"},
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def parse_int(v: str | None) -> int | None:
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def parse_float(v: str | None) -> float | None:
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def to_iso_date(v: str | None) -> str | None:
    """Normalise Meta Kaggle datetimes (e.g. '2019-03-21 23:59:00') to YYYY-MM-DD."""
    if not v:
        return None
    return v.split(" ", 1)[0].strip() or None


def is_truthy(v: str | None) -> bool:
    return (v or "").strip().lower() in {"true", "1", "yes"}


def build(csv_dir: Path, out: Path) -> None:
    tags_path = csv_dir / "Tags.csv"
    comp_path = csv_dir / "Competitions.csv"
    ct_path   = csv_dir / "CompetitionTags.csv"

    for p in (tags_path, comp_path, ct_path):
        if not p.exists():
            sys.exit(f"missing {p}")

    # 1. Tags: TagId -> slug, but only for taxonomy slugs we actually surface.
    tag_id_to_slug: dict[int, str] = {}
    for row in read_csv(tags_path):
        slug = (row.get("Slug") or "").strip().lower()
        if slug in TAXONOMY:
            tid = parse_int(row.get("Id"))
            if tid is not None:
                tag_id_to_slug[tid] = slug

    # 2. CompetitionTags: CompetitionId -> set of tag slugs (filtered).
    comp_tags: dict[int, set[str]] = {}
    for row in read_csv(ct_path):
        cid = parse_int(row.get("CompetitionId"))
        tid = parse_int(row.get("TagId"))
        if cid is None or tid is None:
            continue
        slug = tag_id_to_slug.get(tid)
        if slug is None:
            continue
        comp_tags.setdefault(cid, set()).add(slug)

    # 3. Competitions: keep finalized only, project the fields the UI consumes.
    competitions: list[dict] = []
    for row in read_csv(comp_path):
        if not is_truthy(row.get("FinalLeaderboardHasBeenVerified")):
            continue
        cid = parse_int(row.get("Id"))
        if cid is None:
            continue
        slug_set = comp_tags.get(cid, set())
        # Skip competitions that have no surfaced tag — they're untaggable in
        # our UI and the user would never find them anyway.
        if not slug_set:
            continue
        competitions.append({
            "id": cid,
            "slug": (row.get("Slug") or "").strip(),
            "title": (row.get("Title") or "").strip(),
            "subtitle": (row.get("Subtitle") or "").strip() or None,
            "hostSegment": (row.get("HostSegmentTitle") or "").strip() or None,
            "deadline": to_iso_date(row.get("DeadlineDate")),
            "metric": (row.get("EvaluationAlgorithmName") or "").strip() or None,
            "metricDescription": (row.get("EvaluationAlgorithmDescription") or "").strip() or None,
            "rewardType": (row.get("RewardType") or "").strip() or None,
            "rewardQuantity": parse_float(row.get("RewardQuantity")),
            "tagSlugs": sorted(slug_set),
        })

    # Stable order: most recent deadline first, with nulls last.
    competitions.sort(
        key=lambda c: (c["deadline"] is None, c["deadline"] or ""),
        reverse=True,
    )

    bundle = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "tags": [
            {"slug": slug, "name": meta["name"], "group": meta["group"]}
            for slug, meta in TAXONOMY.items()
        ],
        "competitions": competitions,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        json.dump(bundle, fh, ensure_ascii=False, separators=(",", ":"))

    size_mb = out.stat().st_size / 1_048_576
    print(
        f"wrote {len(competitions)} competitions to {out} "
        f"({size_mb:.2f} MB)",
        file=sys.stderr,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv-dir", type=Path, default=Path("meta-kaggle"),
                    help="Directory with Tags.csv, Competitions.csv, CompetitionTags.csv.")
    ap.add_argument("--out", type=Path, default=Path("static/data/competitions.json"),
                    help="Path to write the JSON bundle.")
    args = ap.parse_args()
    build(args.csv_dir, args.out)


if __name__ == "__main__":
    main()
