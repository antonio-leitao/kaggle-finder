#!/usr/bin/env python3
"""Build static/data/competitions.json from a Meta Kaggle dump.

Reads three CSVs from --csv-dir (Tags.csv, Competitions.csv, CompetitionTags.csv),
keeps every finalized competition, and projects the fields the UI needs.

Tag taxonomy:
- Curated tags get hand-picked names and group assignments (data/task/domain).
- Every other tag found on a finalized competition is included automatically
  with group='other' and `Name` from Meta Kaggle as the display name.

This way no competition is dropped for being tagged with off-piste tags,
and the curated facets stay clean.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Curated taxonomy: hand-picked tags get a clean display name and group.
# Slugs match Meta Kaggle's `tags.Slug` exactly. Anything not in here that
# appears on a finalized competition still gets included, but goes into the
# generic "other" bucket using its raw Name.
CURATED: dict[str, dict[str, str]] = {
    # ---- data ----
    "tabular": {"name": "tabular", "group": "data"},
    "time-series": {"name": "time series", "group": "data"},
    "image-data": {"name": "image data", "group": "data"},
    "text-data": {"name": "text data", "group": "data"},
    "audio-data": {"name": "audio data", "group": "data"},
    "video": {"name": "video", "group": "data"},
    "sequential": {"name": "sequential", "group": "data"},
    "geospatial": {"name": "geospatial", "group": "data"},
    "graphs": {"name": "graphs", "group": "data"},
    # ---- task ----
    "binary-classification": {"name": "binary classification", "group": "task"},
    "multiclass-classification": {"name": "multiclass classification", "group": "task"},
    "multilabel-classification": {"name": "multilabel classification", "group": "task"},
    "classification": {"name": "classification", "group": "task"},
    "regression": {"name": "regression", "group": "task"},
    "forecasting": {"name": "forecasting", "group": "task"},
    "anomaly-detection": {"name": "anomaly detection", "group": "task"},
    "object-detection": {"name": "object detection", "group": "task"},
    "semantic-segmentation": {"name": "semantic segmentation", "group": "task"},
    "instance-segmentation": {"name": "instance segmentation", "group": "task"},
    "ranking": {"name": "ranking", "group": "task"},
    "recommender-systems": {"name": "recommender systems", "group": "task"},
    "clustering": {"name": "clustering", "group": "task"},
    "nlp": {"name": "nlp", "group": "task"},
    "computer-vision": {"name": "computer vision", "group": "task"},
    "reinforcement-learning": {"name": "reinforcement learning", "group": "task"},
    "generative-modeling": {"name": "generative modeling", "group": "task"},
    # ---- domain ----
    "healthcare": {"name": "healthcare", "group": "domain"},
    "medicine": {"name": "medicine", "group": "domain"},
    "biology": {"name": "biology", "group": "domain"},
    "chemistry": {"name": "chemistry", "group": "domain"},
    "physics": {"name": "physics", "group": "domain"},
    "astronomy": {"name": "astronomy", "group": "domain"},
    "earth-and-nature": {"name": "earth and nature", "group": "domain"},
    "environment": {"name": "environment", "group": "domain"},
    "finance": {"name": "finance", "group": "domain"},
    "economics": {"name": "economics", "group": "domain"},
    "manufacturing": {"name": "manufacturing", "group": "domain"},
    "automobile": {"name": "automobile", "group": "domain"},
    "transportation": {"name": "transportation", "group": "domain"},
    "internet": {"name": "internet", "group": "domain"},
    "social-science": {"name": "social science", "group": "domain"},
    "education": {"name": "education", "group": "domain"},
    "energy": {"name": "energy", "group": "domain"},
    "retail-and-shopping": {"name": "retail and shopping", "group": "domain"},
    "arts-and-entertainment": {"name": "arts and entertainment", "group": "domain"},
    "gaming": {"name": "gaming", "group": "domain"},
    "sports": {"name": "sports", "group": "domain"},
    "law-and-government": {"name": "law and government", "group": "domain"},
    "agriculture": {"name": "agriculture", "group": "domain"},
    "food": {"name": "food", "group": "domain"},
}

# Tags we never want to surface (technique/process tags, not subject matter).
# Stripped from the competition's tagSlugs entirely.
BLOCKLIST: set[str] = {
    "beginner",
    "intermediate",
    "advanced",
    "tutorial",
    "tutorials",
    "starter-code",
    "feature-engineering",
    "model-comparison",
    "ensembling",
    "data-cleaning",
    "exploratory-data-analysis",
    "data-visualization",
    "automl",
    "deep-learning",
    "transfer-learning",
    "neural-networks",
    "xgboost",
    "lightgbm",
    "random-forest",
    "logistic-regression",
    "linear-regression",
    "k-means",
    "decision-tree",
    "svm",
    "lstm",
    "gru",
    "transformers",
    "bert",
    "gpt",
    "rnns",
    "cnns",
    "kaggle",
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
    if not v:
        return None
    return v.split(" ", 1)[0].strip() or None


def is_truthy(v: str | None) -> bool:
    return (v or "").strip().lower() in {"true", "1", "yes"}


def humanize(slug: str) -> str:
    return slug.replace("-", " ").strip()


def build(csv_dir: Path, out: Path) -> None:
    tags_path = csv_dir / "Tags.csv"
    comp_path = csv_dir / "Competitions.csv"
    ct_path = csv_dir / "CompetitionTags.csv"
    for p in (tags_path, comp_path, ct_path):
        if not p.exists():
            sys.exit(f"missing {p}")

    # 1. Tags table: TagId -> (slug, raw Name).
    tag_meta: dict[int, tuple[str, str]] = {}
    for row in read_csv(tags_path):
        tid = parse_int(row.get("Id"))
        slug = (row.get("Slug") or "").strip().lower()
        name = (row.get("Name") or "").strip()
        if tid is not None and slug:
            tag_meta[tid] = (slug, name or humanize(slug))

    # 2. Competition -> set of tag slugs (after blocklist filtering).
    comp_tags: dict[int, set[str]] = {}
    for row in read_csv(ct_path):
        cid = parse_int(row.get("CompetitionId"))
        tid = parse_int(row.get("TagId"))
        if cid is None or tid is None:
            continue
        meta = tag_meta.get(tid)
        if meta is None:
            continue
        slug = meta[0]
        if slug in BLOCKLIST:
            continue
        comp_tags.setdefault(cid, set()).add(slug)

    # 3. Build the competition rows. Keep ALL finalized regardless of tags.
    competitions: list[dict] = []
    used_slugs: set[str] = set()
    for row in read_csv(comp_path):
        if not is_truthy(row.get("FinalLeaderboardHasBeenVerified")):
            continue
        cid = parse_int(row.get("Id"))
        if cid is None:
            continue
        slugs = sorted(comp_tags.get(cid, set()))
        used_slugs.update(slugs)
        competitions.append(
            {
                "id": cid,
                "slug": (row.get("Slug") or "").strip(),
                "title": (row.get("Title") or "").strip(),
                "subtitle": (row.get("Subtitle") or "").strip() or None,
                "hostSegment": (row.get("HostSegmentTitle") or "").strip() or None,
                "deadline": to_iso_date(row.get("DeadlineDate")),
                "metric": (row.get("EvaluationAlgorithmName") or "").strip() or None,
                "metricDescription": (
                    row.get("EvaluationAlgorithmDescription") or ""
                ).strip()
                or None,
                "rewardType": (row.get("RewardType") or "").strip() or None,
                "rewardQuantity": parse_float(row.get("RewardQuantity")),
                "tagSlugs": slugs,
            }
        )

    competitions.sort(
        key=lambda c: (c["deadline"] is None, c["deadline"] or ""),
        reverse=True,
    )

    # 4. Tags list: curated first (in declared order, only those actually
    # used), then 'other' tags by usage frequency desc.
    used_freq: Counter[str] = Counter()
    for c in competitions:
        used_freq.update(c["tagSlugs"])

    tags_out: list[dict] = []
    seen: set[str] = set()

    for slug, meta in CURATED.items():
        if slug in used_slugs:
            tags_out.append(
                {"slug": slug, "name": meta["name"], "group": meta["group"]}
            )
            seen.add(slug)

    # Display name lookup (any tag_meta entry with this slug).
    slug_to_name = {s: n for (s, n) in tag_meta.values()}

    other_slugs = sorted(
        used_slugs - seen,
        key=lambda s: (-used_freq[s], s),
    )
    for slug in other_slugs:
        display = slug_to_name.get(slug) or humanize(slug)
        tags_out.append({"slug": slug, "name": display.lower(), "group": "other"})

    bundle = {
        "generatedAt": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "tags": tags_out,
        "competitions": competitions,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        json.dump(bundle, fh, ensure_ascii=False, separators=(",", ":"))

    size_mb = out.stat().st_size / 1_048_576
    n_curated = sum(1 for t in tags_out if t["group"] != "other")
    n_other = len(tags_out) - n_curated
    print(
        f"wrote {len(competitions)} competitions, "
        f"{n_curated} curated tags + {n_other} other "
        f"({size_mb:.2f} MB) to {out}",
        file=sys.stderr,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv-dir", type=Path, default=Path("meta-kaggle"))
    ap.add_argument("--out", type=Path, default=Path("static/data/competitions.json"))
    args = ap.parse_args()
    build(args.csv_dir, args.out)


if __name__ == "__main__":
    main()
