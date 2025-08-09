from app.core.email import send_email
from fastapi import APIRouter, BackgroundTasks, Query

router = APIRouter(prefix="/_debug", tags=["debug"])


@router.post("/mail")
async def debug_mail(background: BackgroundTasks, to: str = Query(...)):
    background.add_task(send_email, to, "FitFolio test", "Hello from Mailpit 👋")
    return {"ok": True}
