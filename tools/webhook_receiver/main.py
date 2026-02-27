from fastapi import FastAPI, Request
from datetime import datetime, timezone

app = FastAPI(title="Webhook Receiver")

EVENTS: list[dict] = []

@app.post("/webhooks/alerts")
async def receive_alert(request: Request):
    body = await request.json()
    event = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "headers": dict(request.headers),
        "body": body,
    }
    EVENTS.append(event)
    if len(EVENTS) > 100:
        del EVENTS[:-100]
    return {"ok": True, "stored": len(EVENTS)}

@app.get("/webhooks/alerts")
def list_alerts(limit: int = 20):
    return EVENTS[-limit:]
