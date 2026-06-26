import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Union

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    settings.start_time = time.time()
    app.state.settings = settings
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check(request: Request) -> dict:
    settings: Settings = request.app.state.settings
    return {
        "status": "healthy",
        "uptime_seconds": time.time() - settings.start_time,
    }


def _parse_content_length(raw: str) -> int:
    stripped = raw.strip()
    if stripped.lower() in ("true", "false"):
        raise ValueError(f"Invalid Content-Length: {raw!r}")
    if "." in stripped:
        raise ValueError(f"Invalid Content-Length: {raw!r}")
    value = int(stripped)
    if value < 0:
        raise ValueError(f"Content-Length must be non-negative, got {value}")
    return value


def _parse_x_echo_status(raw: str) -> int:
    stripped = raw.strip()
    if not stripped:
        raise ValueError("Empty X-Echo-Status")
    if stripped.lower() in ("true", "false"):
        raise ValueError(f"Invalid X-Echo-Status: {raw!r}")
    if "." in stripped:
        raise ValueError(f"Invalid X-Echo-Status: {raw!r}")
    value = int(stripped)
    if not (100 <= value <= 599):
        raise ValueError(f"X-Echo-Status out of range: {value}")
    return value


def _build_query_params(request: Request) -> dict:
    params: dict[str, Union[str, list]] = {}
    for key, value in request.query_params.multi_items():
        if key in params:
            existing = params[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                params[key] = [existing, value]
        else:
            params[key] = value
    return params


@app.api_route("/echo", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def echo_handler(request: Request) -> JSONResponse:
    settings: Settings = request.app.state.settings
    max_size = settings.max_payload_size

    cl_header = request.headers.get("content-length")
    if cl_header is not None:
        try:
            cl_value = _parse_content_length(cl_header)
        except ValueError:
            return JSONResponse(
                status_code=400, content={"detail": "Invalid Content-Length"}
            )
        if cl_value > max_size:
            return JSONResponse(
                status_code=413, content={"detail": "Payload Too Large"}
            )

    echo_status_raw = request.headers.get("x-echo-status")
    response_status = 200
    if echo_status_raw is not None:
        try:
            response_status = _parse_x_echo_status(echo_status_raw)
        except ValueError:
            return JSONResponse(
                status_code=400, content={"detail": "Invalid X-Echo-Status"}
            )

    body_chunks = []
    accumulated = 0
    async for chunk in request.stream():
        accumulated += len(chunk)
        if accumulated > max_size:
            return JSONResponse(
                status_code=413, content={"detail": "Payload Too Large"}
            )
        body_chunks.append(chunk)

    raw_body = b"".join(body_chunks)
    body_str = raw_body.decode("utf-8", errors="replace")

    return JSONResponse(
        status_code=response_status,
        content={
            "method": request.method,
            "headers": dict(request.headers),
            "query_params": _build_query_params(request),
            "body": body_str,
        },
    )


if __name__ == "__main__":
    import uvicorn

    _s = get_settings()
    uvicorn.run("app.main:app", host="0.0.0.0", port=_s.port)
