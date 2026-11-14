"""
Mars Rover Mission Control - front end
Run:   pip install flask
       python app.py
Open:  http://127.0.0.1:5000
"""
import heapq
import json
import math
import random
import os
import urllib.error
import urllib.request
from pathlib import Path

from flask import Flask, jsonify, render_template, request

BASE = Path(__file__).parent
app = Flask(__name__)


# FastAPI backend address. Override with MARS_BACKEND_URL in deployment.
MARS_BACKEND_URL = os.environ.get("MARS_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


def backend_request(path, method="GET", payload=None, timeout=8):
    """Call the FastAPI service and return decoded JSON."""
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        MARS_BACKEND_URL + path,
        data=data,
        headers=headers,
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8")), response.status
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            detail = {"detail": "FastAPI returned an HTTP error."}
        return detail, exc.code
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return {
            "status": "offline",
            "detail": "FastAPI backend is unreachable. Start Backend/Main.py on port 8000."
        }, 503



def load_grid():
    with open(BASE / "static" / "grid.json") as f:
        return json.load(f)


def astar(grid, start, goal):
    """8-direction A* on a grid where 1 = obstacle. start/goal are (x, y)."""
    h, w = len(grid), len(grid[0])
    sx, sy = start
    gx, gy = goal
    if grid[sy][sx] or grid[gy][gx]:
        return None, 0

    def heuristic(x, y):  # octile distance
        dx, dy = abs(x - gx), abs(y - gy)
        return (dx + dy) + (math.sqrt(2) - 2) * min(dx, dy)

    open_heap = [(heuristic(sx, sy), 0.0, (sx, sy))]
    came, best, closed = {}, {(sx, sy): 0.0}, set()
    explored = 0
    while open_heap:
        _, g, cur = heapq.heappop(open_heap)
        if cur in closed:
            continue
        closed.add(cur)
        explored += 1
        if cur == (gx, gy):
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            return path[::-1], explored
        x, y = cur
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if not (0 <= nx < w and 0 <= ny < h) or grid[ny][nx]:
                    continue
                if dx and dy and (grid[y][nx] or grid[ny][x]):
                    continue  # no cutting corners past rocks
                ng = g + (math.sqrt(2) if dx and dy else 1)
                if ng < best.get((nx, ny), 1e9):
                    best[(nx, ny)] = ng
                    came[(nx, ny)] = cur
                    heapq.heappush(open_heap, (ng + heuristic(nx, ny), ng, (nx, ny)))
    return None, explored


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/grid")
def api_grid():
    return jsonify(load_grid())


@app.route("/api/random")
def api_random():
    size = load_grid()["width"]
    density = float(request.args.get("density", 0.18))
    grid = [[1 if random.random() < density else 0 for _ in range(size)] for _ in range(size)]
    grid[0][0] = grid[size - 1][size - 1] = 0
    return jsonify({"width": size, "height": size, "grid": grid})


@app.route("/api/path", methods=["POST"])
def api_path():
    d = request.get_json(force=True)
    path, explored = astar(d["grid"], tuple(d["start"]), tuple(d["goal"]))
    if path is None:
        return jsonify({"found": False, "explored": explored})
    dist = sum(math.dist(a, b) for a, b in zip(path, path[1:]))
    return jsonify({"found": True, "path": path, "explored": explored,
                    "steps": len(path) - 1, "cost": round(dist, 2)})


# ---------------- FastAPI integration proxy ----------------
# Browser requests stay same-origin; Flask safely forwards them to FastAPI.

@app.route("/api/backend/status")
def backend_status():
    data, status = backend_request("/system/status")
    data["http_status"] = status
    data["backend_url"] = MARS_BACKEND_URL
    return jsonify(data), status


@app.route("/api/backend/layers")
def backend_layers():
    data, status = backend_request("/nasa/layers")
    return jsonify(data), status


@app.route("/api/backend/layer/<layer_id>/capabilities")
def backend_layer_capabilities(layer_id):
    data, status = backend_request(
        f"/nasa/layers/{layer_id}/capabilities", timeout=15
    )
    return jsonify(data), status


@app.route("/api/backend/mission/plan", methods=["POST"])
def backend_mission_plan():
    payload = request.get_json(silent=True) or {}
    data, status = backend_request(
        "/mars/mission/plan", method="POST", payload=payload
    )
    return jsonify(data), status


if __name__ == "__main__":
    print("Mission control online -> http://127.0.0.1:5000")
    app.run(debug=True)
