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
from pathlib import Path

from flask import Flask, jsonify, render_template, request

BASE = Path(__file__).parent
app = Flask(__name__)


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


if __name__ == "__main__":
    print("Mission control online -> http://127.0.0.1:5000")
    app.run(debug=True)
