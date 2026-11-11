import random
import time

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

app = FastAPI(title="SentinelOps Demo App")

REQUESTS = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
)
LATENCY = Histogram(
    "http_request_duration_seconds", "Request latency in seconds", ["path"]
)


@app.middleware("http")
async def track_metrics(request: Request, call_next):
    start = time.time()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        LATENCY.labels(request.url.path).observe(time.time() - start)
        REQUESTS.labels(request.method, request.url.path, str(status)).inc()


@app.get("/")
def home():
    return {"message": "SentinelOps demo app is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/slow")
def slow():
    time.sleep(random.uniform(0.5, 2.0))
    return {"message": "slow response"}


@app.get("/error")
def error():
    raise HTTPException(status_code=500, detail="Simulated failure")


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)