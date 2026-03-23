"""OpenClaw API routes — pipeline execution, freelance cycle, status."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

router = APIRouter(prefix="/openclaw", tags=["OpenClaw"])

# Valid platforms for dispatch
_VALID_PLATFORMS = {"freelancer", "upwork", "fiverr", "pph", "guru"}
_VALID_ACTIONS = {"bid", "propose", "deliver", "quote", "scan", "apply"}


class PipelineRequest(BaseModel):
    name: str
    provider: str = "openai"
    variables: dict = {}

    @field_validator("name")
    @classmethod
    def name_must_be_safe(cls, v: str) -> str:
        if not v.isidentifier() and not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid pipeline name: {v!r}")
        return v


class CycleRequest(BaseModel):
    platforms: list[str] | None = None
    scan_only: bool = False


class DispatchRequest(BaseModel):
    platform: str
    action: str
    job_data: dict = {}
    provider: str = "openai"

    @field_validator("platform")
    @classmethod
    def platform_must_be_valid(cls, v: str) -> str:
        if v not in _VALID_PLATFORMS:
            raise ValueError(f"Unknown platform '{v}'. Valid: {sorted(_VALID_PLATFORMS)}")
        return v

    @field_validator("action")
    @classmethod
    def action_must_be_valid(cls, v: str) -> str:
        if v not in _VALID_ACTIONS:
            raise ValueError(f"Unknown action '{v}'. Valid: {sorted(_VALID_ACTIONS)}")
        return v


@router.get("/status")
def openclaw_status():
    from openclaw.engine import OpenClawEngine
    return OpenClawEngine().status()


@router.post("/pipeline")
def run_pipeline(req: PipelineRequest):
    from openclaw.engine import OpenClawEngine
    engine = OpenClawEngine()
    return engine.run_pipeline(req.name, provider=req.provider, **req.variables)


@router.get("/pipelines")
def list_pipelines():
    from openclaw.engine import OpenClawEngine
    return {"pipelines": OpenClawEngine().list_pipelines()}


@router.post("/cycle")
def freelance_cycle(req: CycleRequest):
    from openclaw.engine import OpenClawEngine
    engine = OpenClawEngine()
    return engine.freelance_cycle(platforms=req.platforms, scan_only=req.scan_only)


@router.get("/revenue")
def revenue():
    from openclaw.engine import OpenClawEngine
    return OpenClawEngine().reconcile_revenue()


@router.post("/dispatch")
def dispatch_platform_work(req: DispatchRequest):
    from openclaw.engine import OpenClawEngine
    engine = OpenClawEngine()
    return engine.dispatch_platform_work(
        platform=req.platform,
        action=req.action,
        job_data=req.job_data,
        provider=req.provider,
    )
