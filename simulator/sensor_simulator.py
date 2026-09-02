"""Configurable CSV sensor-data simulator for coal-mine subsidence monitoring."""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, Literal

CSV_COLUMNS = (
    "node_id", "timestamp", "position_x", "position_y", "tilt_x", "tilt_y",
    "vibration_rms", "vibration_peak", "crack_width",
)

#............MODULE....................................................................................................

Scenario = Literal["normal", "deteriorating", "dangerous_event"]
@dataclass(frozen=True)
class NodeConfig:
    """ position and operating scenario for a sensor node."""
    node_id: str
    x: float
    y: float
    scenario: Scenario = "normal"


class SensorSimulator:
    """Generate plausible, repeatable readings for one or more sensor nodes."""
    # `seed` makes a demonstration deterministic. The scenario progression is based on emitted ticks rather than wall-clock time, so it also behaves predictably in tests and when the caller runs faster than real time.

    def __init__(self, nodes: list[NodeConfig], seed: int | None = None) -> None:
        if not nodes:
            raise ValueError("At least one sensor node is required.")
        self.nodes = nodes
        self._random = random.Random(seed)
        self._ticks = {node.node_id: 0 for node in nodes}
        self._baselines = {
            node.node_id: {
                "tilt_x": self._random.uniform(-0.12, 0.12),
                "tilt_y": self._random.uniform(-0.12, 0.12),
                "rms": self._random.uniform(0.05, 0.14),
                "crack": self._random.uniform(0.05, 0.25),
            }
            for node in nodes
        }

    def reading(self, node: NodeConfig, timestamp: datetime | None = None) -> dict:
        """Return the next reading in the agreed logical sensor schema."""
        tick = self._ticks[node.node_id]
        self._ticks[node.node_id] += 1
        timestamp = timestamp or datetime.now(timezone.utc)
        baseline = self._baselines[node.node_id]

        tilt_x = baseline["tilt_x"] + self._noise(0.025)
        tilt_y = baseline["tilt_y"] + self._noise(0.025)
        rms = baseline["rms"] + self._noise(0.018)
        crack = baseline["crack"] + self._noise(0.015)

        if node.scenario == "deteriorating":
            # Slow persistent ground movement, with occasional micro-vibration.
            progress = min(tick / 300, 1.0)
            tilt_x += 1.8 * progress + self._noise(0.04)
            tilt_y += 1.3 * progress + self._noise(0.04)
            rms += 0.38 * progress + 0.05 * math.sin(tick / 9)
            crack += 2.6 * progress
        elif node.scenario == "dangerous_event":
            # A sharp vibration event followed by sustained displacement signs.
            event_strength = 0.35 + 1.65 * (1 - math.exp(-tick / 18))
            transient = 0.45 * max(0.0, math.sin(tick * 1.7))
            tilt_x += 2.6 * (1 - math.exp(-tick / 35))
            tilt_y += 2.1 * (1 - math.exp(-tick / 35))
            rms += event_strength + transient
            crack += 3.8 * (1 - math.exp(-tick / 30))

        rms = max(0.01, rms)
        # Peak is always at least RMS, and becomes more pronounced under events.
        peak = rms * self._random.uniform(1.35, 2.25)
        if node.scenario == "dangerous_event":
            peak += self._random.uniform(0.5, 1.6)

        return {
            "node_id": node.node_id,
            "timestamp": timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "position": {"x": round(node.x, 2), "y": round(node.y, 2)},
            "tilt": {"x": round(tilt_x, 3), "y": round(tilt_y, 3)},
            "vibration": {"rms": round(rms, 3), "peak": round(peak, 3)},
            "crack_width": round(max(0.0, crack), 3),
        }

    def readings(self, timestamp: datetime | None = None) -> list[dict]:
        """Return one complete tick: a reading from every configured node."""
        timestamp = timestamp or datetime.now(timezone.utc)
        return [self.reading(node, timestamp) for node in self.nodes]

    def stream(self, interval_seconds: float) -> Iterator[dict]:
        """Yield readings continuously, pacing complete ticks at the interval."""
        while True:
            for item in self.readings():
                yield item
            time.sleep(interval_seconds)

    def _noise(self, spread: float) -> float:
        return self._random.uniform(-spread, spread)

# ................................................................................................................

def as_csv_row(reading: dict) -> dict:
    """Flatten a logical reading to the hardware CSV column format."""
    return {
        "node_id": reading["node_id"],
        "timestamp": reading["timestamp"],
        "position_x": reading["position"]["x"],
        "position_y": reading["position"]["y"],
        "tilt_x": reading["tilt"]["x"],
        "tilt_y": reading["tilt"]["y"],
        "vibration_rms": reading["vibration"]["rms"],
        "vibration_peak": reading["vibration"]["peak"],
        "crack_width": reading["crack_width"],
    }
DEFAULT_NODES = [
    NodeConfig("NODE_01", 0.0, 0.0, "normal"),
    NodeConfig("NODE_02", 40.0, 15.0, "deteriorating"),
    NodeConfig("NODE_03", 85.0, 30.0, "dangerous_event"),
]
def parse_nodes(value: str) -> list[NodeConfig]:
    """Parse ``ID,X,Y,SCENARIO;...`` supplied through the command line."""
    nodes: list[NodeConfig] = []
    allowed = {"normal", "deteriorating", "dangerous_event"}
    for item in value.split(";"):
        parts = [part.strip() for part in item.split(",")]
        if len(parts) != 4 or parts[3] not in allowed:
            raise argparse.ArgumentTypeError(
                "Nodes must be ID,X,Y,SCENARIO;... where scenario is "
                "normal, deteriorating, or dangerous_event."
            )
        try:
            nodes.append(NodeConfig(parts[0], float(parts[1]), float(parts[2]), parts[3]))
        except ValueError as error:
            raise argparse.ArgumentTypeError("Node coordinates must be numbers.") from error
    return nodes
def main() -> None:
    parser = argparse.ArgumentParser(description="Emit simulated mine-monitoring readings as CSV.")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between complete ticks (default: 1).")
    parser.add_argument("--count", type=int, default=0, help="Ticks to emit; 0 runs continuously (default: 0).")
    parser.add_argument("--seed", type=int, help="Optional seed for repeatable sample data.")
    parser.add_argument(
        "--output", metavar="PATH",
        help="CSV destination (default: standard output). Example: --output simulated_readings.csv",
    )
    parser.add_argument(
        "--nodes", type=parse_nodes, default=DEFAULT_NODES,
        help="ID,X,Y,SCENARIO entries separated by semicolons.",
    )
    args = parser.parse_args()
    if args.interval < 0 or args.count < 0:
        parser.error("--interval and --count must be non-negative.")

    simulator = SensorSimulator(args.nodes, seed=args.seed)
    output = open(args.output, "w", encoding="utf-8", newline="") if args.output else sys.stdout
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    output.flush()
    tick = 0
    try:
        for reading in simulator.stream(args.interval):
            writer.writerow(as_csv_row(reading))
            output.flush()
            # A tick finishes after each configured node has emitted once.
            if reading["node_id"] == args.nodes[-1].node_id:
                tick += 1
                if args.count and tick >= args.count:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        if output is not sys.stdout:
            output.close()
if __name__ == "__main__":
    main()
