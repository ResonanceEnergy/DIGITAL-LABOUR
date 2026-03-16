"""OpenClaw API routes — pipeline execution, freelance cycle, status."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/openclaw", tags=["OpenClaw"])


class PipelineRequest(BaseModel):
    name: str
    provider: str = "openai"
    variables: dict = {}


class CycleRequest(BaseModel):
    platforms: list[str] | None = None
    scan_only: bool = False


class DispatchRequest(BaseModel):
    platform: str
    action: str
    job_data: dict = {}
    provider: str = "openai"


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
