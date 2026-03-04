"""
Autonomous Anomaly Detection & Response Agent — FastAPI Backend
Serves the premium dashboard and provides REST API endpoints for
dataset upload, anomaly detection, real-time streaming, and statistics.
"""

import os
import json
import csv
import io
import time
import asyncio
import logging
from typing import List, Dict, Any
from threading import Thread

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from ml_detection import AnomalyDetectorEnsemble
from reasoning_agent import ReasoningAgent
from actions import ActionSimulator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DashboardAPI")

app = FastAPI(title="Autonomous Anomaly Detection & Response Agent", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LOG_FILE = "system_events.json"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

# Global instances
ml_engine = AnomalyDetectorEnsemble()
agent = None  # Lazy-loaded to avoid LangGraph import delay

# SSE clients
sse_clients: List[asyncio.Queue] = []

# Simulation state
simulation_running = False


def get_agent():
    global agent
    if agent is None:
        agent = ReasoningAgent()
    return agent


def load_events() -> List[Dict[str, Any]]:
    if not os.path.exists(LOG_FILE):
        return []
    events = []
    with open(LOG_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def append_event(event: Dict[str, Any]):
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(event) + "\n")


async def broadcast_event(event: Dict[str, Any]):
    dead = []
    for q in sse_clients:
        try:
            await q.put(event)
        except Exception:
            dead.append(q)
    for q in dead:
        sse_clients.remove(q)


# ── API Endpoints ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/events")
async def get_events():
    return load_events()


@app.get("/api/stats")
async def get_stats():
    events = load_events()
    if not events:
        return {
            "total_events": 0,
            "anomaly_count": 0,
            "normal_count": 0,
            "anomaly_rate": 0,
            "avg_mttr_ms": 0,
            "avg_cpu": 0,
            "avg_memory": 0,
            "avg_latency": 0,
            "root_causes": {},
            "actions_taken": {},
        }

    anomalies = [e for e in events if e.get("is_anomaly")]
    normals = [e for e in events if not e.get("is_anomaly")]

    # Root cause breakdown
    root_causes = {}
    actions_taken = {}
    for e in anomalies:
        rc = e.get("root_cause", "Unknown")
        root_causes[rc] = root_causes.get(rc, 0) + 1
        act = e.get("selected_action", "none")
        actions_taken[act] = actions_taken.get(act, 0) + 1

    processing_times = [e.get("processing_time_ms", 0) for e in events if e.get("processing_time_ms")]

    return {
        "total_events": len(events),
        "anomaly_count": len(anomalies),
        "normal_count": len(normals),
        "anomaly_rate": round(len(anomalies) / len(events) * 100, 2) if events else 0,
        "avg_mttr_ms": round(sum(processing_times) / len(processing_times), 2) if processing_times else 0,
        "avg_cpu": round(sum(e.get("cpu_usage", 0) for e in events) / len(events), 2),
        "avg_memory": round(sum(e.get("memory_usage", 0) for e in events) / len(events), 2),
        "avg_latency": round(sum(e.get("latency", 0) for e in events) / len(events), 2),
        "root_causes": root_causes,
        "actions_taken": actions_taken,
    }


@app.post("/api/upload-dataset")
async def upload_dataset(file: UploadFile = File(...)):
    """Upload a CSV or JSON dataset for anomaly detection analysis."""
    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("csv", "json"):
        raise HTTPException(400, "Only CSV and JSON files are supported")

    content = await file.read()
    text = content.decode("utf-8")

    rows = []
    if ext == "csv":
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            rows.append({k: _try_float(v) for k, v in row.items()})
    else:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                rows = parsed
            else:
                # JSONL format
                for line in text.strip().split("\n"):
                    if line.strip():
                        rows.append(json.loads(line))
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid JSON format")

    if not rows:
        raise HTTPException(400, "Dataset is empty")

    # Run detection on each row
    results = []
    reasoning = get_agent()
    for row in rows:
        result = reasoning.process_event(row)
        entry = {
            "timestamp": row.get("timestamp", time.time()),
            "cpu_usage": row.get("cpu_usage", 0),
            "memory_usage": row.get("memory_usage", 0),
            "latency": row.get("latency", 0),
            "error_rate": row.get("error_rate", 0),
            "is_anomaly": result["ml_analysis"].get("is_anomaly", False),
            "confidence": result["ml_analysis"].get("confidence", 0.0),
            "root_cause": result.get("root_cause"),
            "selected_action": result.get("selected_action"),
            "action_result": result.get("action_result"),
            "processing_time_ms": result.get("processing_time_ms", 0.0),
        }
        results.append(entry)
        append_event(entry)

    anomalies = [r for r in results if r["is_anomaly"]]
    return {
        "filename": file.filename,
        "total_rows": len(results),
        "anomalies_detected": len(anomalies),
        "results": results,
    }


@app.post("/api/detect")
async def detect_single(data: Dict[str, Any]):
    """Run anomaly detection on a single data point."""
    result = ml_engine.predict(data)
    return result


@app.post("/api/simulate/start")
async def start_simulation():
    """Start a real-time simulation using mock data generation."""
    global simulation_running
    if simulation_running:
        return {"status": "already_running"}

    simulation_running = True

    async def run_sim():
        global simulation_running
        import random
        reasoning = get_agent()
        while simulation_running:
            is_anomaly_event = random.random() < 0.08
            event = {
                "timestamp": time.time(),
                "cpu_usage": round(random.uniform(80, 100), 2) if is_anomaly_event else round(random.uniform(10, 60), 2),
                "memory_usage": round(random.uniform(85, 99), 2) if is_anomaly_event else round(random.uniform(20, 70), 2),
                "latency": round(random.uniform(200, 1500), 2) if is_anomaly_event else round(random.uniform(10, 100), 2),
                "error_rate": round(random.uniform(0.1, 0.5), 4) if is_anomaly_event else round(random.uniform(0.001, 0.01), 4),
            }
            result = reasoning.process_event(event)
            entry = {
                "timestamp": event["timestamp"],
                "cpu_usage": event["cpu_usage"],
                "memory_usage": event["memory_usage"],
                "latency": event["latency"],
                "error_rate": event["error_rate"],
                "is_anomaly": result["ml_analysis"].get("is_anomaly", False),
                "confidence": result["ml_analysis"].get("confidence", 0.0),
                "root_cause": result.get("root_cause"),
                "selected_action": result.get("selected_action"),
                "action_result": result.get("action_result"),
                "processing_time_ms": result.get("processing_time_ms", 0.0),
            }
            append_event(entry)
            await broadcast_event(entry)
            await asyncio.sleep(1.5)

    asyncio.create_task(run_sim())
    return {"status": "started"}


@app.post("/api/simulate/stop")
async def stop_simulation():
    global simulation_running
    simulation_running = False
    return {"status": "stopped"}


@app.get("/api/simulate/status")
async def simulation_status():
    return {"running": simulation_running}


@app.get("/api/stream")
async def event_stream():
    """SSE endpoint for real-time event push."""
    queue: asyncio.Queue = asyncio.Queue()
    sse_clients.append(queue)

    async def generate():
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in sse_clients:
                sse_clients.remove(queue)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/clear-events")
async def clear_events():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    return {"status": "cleared"}


# ── Helpers ──────────────────────────────────────────────

def _try_float(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return v


# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
