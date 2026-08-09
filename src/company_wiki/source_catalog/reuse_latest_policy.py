"""WU-1102~1104: exact/latest/download closure helpers — ported from the
frozen Phase-2 contract (ADR WU-203).  Exact requests never discover;
latest gaps are exactly the missing periods; download authorization binds
the immutable GapPlan + policy hash + expiry.
"""

from __future__ import annotations

import hashlib
import json


def exact_decision(*, has_valid_handle: bool, allow_download: bool = False,
                   allow_discovery: bool = False) -> str:
    """exact 状态机：有效 handle 永远直接复用，绝不 discovery。"""
    if has_valid_handle:
        return "REUSED"
    if allow_download:
        return "DOWNLOAD"
    return "NOT_FOUND"


def latest_gap(covered: set[str], discovered: set[str]) -> list[str]:
    """缺期 = discovered − covered，排序去重；covered 永不出现在 gap。"""
    return sorted(discovered - covered)


def authorization_valid(
    auth: dict,
    *,
    gap_plan_hash: str,
    policy_hash: str,
    now: str,
) -> bool:
    """授权必须绑定 gap plan hash + policy hash + 未过期。"""
    if auth.get("gap_plan_hash") != gap_plan_hash:
        return False
    if auth.get("policy_hash") != policy_hash:
        return False
    if now > auth.get("expires_at", ""):
        return False
    return True


def canonical_gap_hash(missing: list[str], *, covered: set[str]) -> str:
    """确定性 GapPlan 标识（绑定缺期与已覆盖集合，供授权引用）。"""
    payload = json.dumps(
        {"missing": sorted(missing), "covered": sorted(covered)},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
