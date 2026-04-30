"""TLC model checker utilities."""
import json
import subprocess
from pathlib import Path

import networkx as nx

_LIB_DIR = Path(__file__).parent
_PROJECT_ROOT = _LIB_DIR.parent
_JAVA_HOME = "/opt/homebrew/opt/openjdk"
_TLA2TOOLS = _PROJECT_ROOT / "tlaplus/tlatools/org.lamport.tlatools/dist/tla2tools.jar"


def _check_tlc():
    if not _TLA2TOOLS.exists():
        raise RuntimeError(f"TLC not found at {_TLA2TOOLS}. Run ./build-tlc.sh first.")


def run(spec_path: str | Path, output_format: str = "json", output_name: str = None):
    """Run TLC on a spec and dump state graph.

    Args:
        spec_path: Path to .tla file
        output_format: "json" for post-processing or "dot" for graphviz
        output_name: Base name for output files (defaults to spec name)
    """
    _check_tlc()
    spec_path = Path(spec_path)
    if output_name is None:
        output_name = spec_path.stem

    subprocess.check_call([
        "java", "-jar", str(_TLA2TOOLS),
        "-deadlock",
        spec_path.name,
        "-dump", output_format, output_name,
    ], env={
        "JAVA_HOME": f"{_JAVA_HOME}/bin/",
        "PATH": f"{_JAVA_HOME}/bin/:$PATH"
    }, cwd=spec_path.parent)

    if output_format == "dot":
        dot_path = spec_path.parent / f"{output_name}.dot"
        pdf_path = spec_path.parent / f"{output_name}.pdf"
        subprocess.check_call(["dot", "-Tpdf", dot_path, "-o", pdf_path])


def parse_state_graph(base_path: str | Path) -> tuple[nx.DiGraph, dict, dict]:
    """Parse TLC's JSON state graph output.

    Args:
        base_path: Path without extension, e.g. "MuddyChildren" or "card-game/CardGame"

    Returns:
        (G, node_map, edge_actions) where:
        - G is a directed graph with state fingerprints as nodes
        - node_map maps fingerprints to state values
        - edge_actions maps (from_fp, to_fp) to edge metadata including action name
    """
    base_path = Path(base_path)
    states_path = base_path.parent / f"{base_path.name}-states.json"
    edges_path = base_path.parent / f"{base_path.name}-edges.json"

    G = nx.DiGraph()
    edge_actions = {}

    with open(edges_path) as f:
        for edge in json.load(f)["edges"]:
            G.add_edge(edge["from"], edge["to"])
            edge_actions[(edge["from"], edge["to"])] = edge

    node_map = {}
    with open(states_path) as f:
        for node in json.load(f)["states"]:
            node_map[node["fp"]] = node["val"]

    return G, node_map, edge_actions
