#!/usr/bin/env python3
"""Knowledge analysis for CardGame spec."""
import subprocess
import sys
from pathlib import Path

from networkx.drawing.nx_pydot import write_dot

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib import tlc, kripke

THIS_DIR = Path(__file__).parent


def state_label(state: dict) -> str:
    deal = state["deal"]
    return f"1:{deal[0]} 2:{deal[1]} T:{deal[2]}"


if __name__ == "__main__":
    tlc.run(THIS_DIR / "CardGame.tla")
    G, node_map, edge_actions = tlc.parse_state_graph(THIS_DIR / "CardGame")
    print(f"TLC state graph: {len(G.nodes())} nodes, {len(G.edges())} edges")

    # Filter to initial states only (pc = "Skip" for both agents)
    filtered_states = {
        fp: val for fp, val in node_map.items()
        if val["pc"] == ["Skip", "Skip"]
    }
    print(f"States (excluding Done): {len(filtered_states)}")
    kripke.validate_state_transitions(G, filtered_states)

    eq_classes = kripke.build_equivalence_classes(filtered_states)
    indist_G, agents = kripke.build_indistinguishability_graph(filtered_states, eq_classes)
    print(f"Agents: {agents}")
    print(f"Indistinguishability graph: {len(indist_G.nodes())} nodes, {len(indist_G.edges())} edges")

    for fp in indist_G.nodes():
        indist_G.nodes[fp]["label"] = state_label(filtered_states[fp])
    for u, v, data in indist_G.edges(data=True):
        indist_G.edges[u, v]["label"] = ",".join(data["agents"])

    indist_G.graph["graph"] = {"overlap": "false"}

    dot_path = THIS_DIR / "CardGame-indistinguishability.dot"
    write_dot(indist_G, dot_path)
    print(f"Wrote {dot_path}")

    pdf_path = THIS_DIR / "CardGame-indistinguishability.pdf"
    subprocess.check_call(["neato", "-Tpdf", dot_path, "-o", pdf_path])
    print(f"Wrote {pdf_path}")
