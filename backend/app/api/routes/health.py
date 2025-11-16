from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.api_route("/healthz", methods=["GET", "HEAD"], include_in_schema=False)
def healthz():
    return {"status": "ok"}
