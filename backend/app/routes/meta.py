from fastapi import APIRouter

from app.constants.cluster_kinds import CLUSTER_KIND_META, CLUSTER_KIND_ORDER
from app.constants.roles import ROLE_META, ROLES
from app.constants.rfm import BUDGET_MAX, BUDGET_MIN, COUPON_TIERS, DEFAULT_BUDGET, K_MAX, K_MIN
from app.constants.segment_status import SEGMENT_STATUS
from app.constants.strategy_status import STRATEGY_STATUS

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/enums")
def enums() -> dict:
    return {
        "roles": [{"value": role, **ROLE_META[role]} for role in ROLES],
        "segment_status": [{"value": key, "label": label} for key, label in SEGMENT_STATUS.items()],
        "strategy_status": [{"value": key, "label": label} for key, label in STRATEGY_STATUS.items()],
        "cluster_kinds": [
            {"value": kind, **CLUSTER_KIND_META[kind]} for kind in CLUSTER_KIND_ORDER
        ],
        "rfm": {
            "score_min": 1,
            "score_max": 5,
            "k_min": K_MIN,
            "k_max": K_MAX,
            "coupon_tiers": list(COUPON_TIERS),
            "budget_min": BUDGET_MIN,
            "budget_max": BUDGET_MAX,
            "default_budget": DEFAULT_BUDGET,
        },
    }
