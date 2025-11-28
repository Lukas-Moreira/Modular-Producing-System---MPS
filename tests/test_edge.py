# tests/test_edge.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.append(str(SRC))

from modules.edge_monitor import EdgeMonitor 

def on_edge(addr, edge, old, new):
    print(f">>> Borda: addr={addr}, edge={edge}, {old} -> {new}")

mapping = {"start_address": 0, "count": 5}
monitor = EdgeMonitor(mapping=mapping)
monitor.register_callback(on_edge)

snapshots = [
    {0: False, 1: False, 2: False, 3: False, 4: False},
    {0: True,  1: False, 2: False, 3: False, 4: False},
    {0: True,  1: True,  2: False, 3: False, 4: False},
    {0: False, 1: True,  2: False, 3: True,  4: False},
]

for snap in snapshots:
    events = monitor.process_snapshot(snap)
    print("Eventos:", events)
