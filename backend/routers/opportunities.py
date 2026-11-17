from fastapi import APIRouter
from src.agents.scorer import score_all_clients

router = APIRouter(tags=["opportunities"])


@router.get("/opportunities")
def get_opportunities(
    opp_type: str = "All",
    industry: str = "All",
    demo_only: bool = False,
) -> list[dict]:
    results = score_all_clients()          # returns from cache after first call
    if opp_type != "All":
        results = [r for r in results if r["opportunity_type"] == opp_type]
    if industry != "All":
        results = [r for r in results if r["industry"] == industry]
    if demo_only:
        results = [r for r in results if r.get("is_demo_scenario")]
    return results


@router.get("/opportunities/meta")
def get_opportunities_meta() -> dict:
    """Filter options — derived from the same cached scoring run."""
    results = score_all_clients()
    return {
        "types":      sorted({r["opportunity_type"] for r in results}),
        "industries": sorted({r["industry"]          for r in results}),
    }
