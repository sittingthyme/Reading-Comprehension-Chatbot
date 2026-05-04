"""
Aggregate scores for CAIQ-PANAS (full and mini).
"""
from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List

from .caiq_panas_items import (
    CAIQ_FULL_ITEMS,
    MINI_CAIQ_IDS,
    MINI_PANAS_IDS,
    PANAS_FULL_ITEMS,
    SurveyVersion,
)


def _vals_by_ids(responses: Dict[str, int], ids: List[str]) -> List[float]:
    out = []
    for iid in ids:
        v = responses.get(iid)
        if v is None:
            raise ValueError(f"missing item {iid}")
        out.append(float(v))
    return out


def compute_scores(version: SurveyVersion, responses: Dict[str, int]) -> Dict[str, Any]:
    """
    responses: item_id -> 1..5 for all items in that survey version.
    """
    if version == "full":
        caiq_ids = [it.item_id for it in CAIQ_FULL_ITEMS]
        caiq_vals = _vals_by_ids(responses, caiq_ids)
        caiq_total = mean(caiq_vals)
        pa_ids = [it.item_id for it in PANAS_FULL_ITEMS if it.item_id.startswith("PANAS_PA")]
        na_ids = [it.item_id for it in PANAS_FULL_ITEMS if it.item_id.startswith("PANAS_NA")]
        pos = mean(_vals_by_ids(responses, pa_ids))
        neg = mean(_vals_by_ids(responses, na_ids))
        return {
            "version": "full",
            "caiqTotalMean": round(caiq_total, 4),
            "panasPositiveMean": round(pos, 4),
            "panasNegativeMean": round(neg, 4),
            "overallAffect": round(pos - neg, 4),
            "caiqItemScores": {iid: responses[iid] for iid in caiq_ids},
        }

    # mini: 6 CAIQ individual; PANAS pos = mean PA2,PA3; neg = mean NA4,NA5
    caiq_scores = {iid: responses[iid] for iid in MINI_CAIQ_IDS}
    pos = mean(_vals_by_ids(responses, list(MINI_PANAS_IDS[:2])))  # PA2, PA3
    neg = mean(_vals_by_ids(responses, list(MINI_PANAS_IDS[2:])))  # NA4, NA5
    return {
        "version": "mini",
        "caiqItemScores": caiq_scores,
        "panasPositiveMiniMean": round(pos, 4),
        "panasNegativeMiniMean": round(neg, 4),
        "overallAffectMini": round(pos - neg, 4),
    }
