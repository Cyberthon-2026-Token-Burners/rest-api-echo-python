import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request

from app.config import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    settings.start_time = time.time()
    app.state.settings = settings
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check() -> dict:
    settings: Settings = app.state.settings
    return {
        "status": "ok",
        "uptime": time.time() - settings.start_time,
    }


@app.post("/echo")
async def echo_handler(request: Request) -> dict:
    settings: Settings = app.state.settings
    body = await request.body()
    if len(body) > settings.max_payload_size:
        from fastapi import HTTPException

        raise HTTPException(status_code=413, detail="Payload too large")
    return {
        "headers": dict(request.headers),
        "body": body.decode("utf-8", errors="replace"),
        "query_params": dict(request.query_params),
    }


if __name__ == "__main__":
    import uvicorn

    _s = get_settings()
    uvicorn.run("app.main:app", host="0.0.0.0", port=_s.port)
