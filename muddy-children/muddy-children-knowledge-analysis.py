#!/usr/bin/env python3
"""Knowledge analysis for MuddyChildren spec."""
import subprocess
import sys
from pathlib import Path

from networkx.drawing.nx_pydot import write_dot

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib import tlc, knowledge

THIS_DIR = Path(__file__).parent


def state_label(state: dict) -> str:
    """Create a human-readable label for a state."""
    muddy = state["muddy"]
    q = state["q"]
    saidYes = state["saidYes"]
    # muddy is indexed by child (0-indexed in JSON)
    muddy_str = ",".join(str(i + 1) for i, v in enumerate(muddy) if v) or "none"
    # saidYes[i] is the set of who said yes (same for all i), take first
    first_said_yes = saidYes[0] if saidYes else []
    yes_str = ",".join(str(i) for i in sorted(first_said_yes)) or "none"
    # q[i] is the same for all i, take first
    q_val = q[0] if q else 0
    return f"muddy:{muddy_str} yes:{yes_str} q={q_val}"


if __name__ == "__main__":
    tlc.run(THIS_DIR / "MuddyChildren.tla")
    G, node_map, edge_actions = tlc.parse_state_graph(THIS_DIR / "MuddyChildren")
    print(f"TLC state graph: {len(G.nodes())} nodes, {len(G.edges())} edges")

    # Filter out "Done" states
    filtered_states = {fp: val for fp, val in node_map.items() if val["pc"]["0"] != "Done"}
    print(f"States (excluding Done): {len(filtered_states)}")

    indist_G, agents = knowledge.build_indistinguishability_graph(filtered_states)
    print(f"Agents: {agents}")
    print(f"Indistinguishability graph: {len(indist_G.nodes())} nodes, {len(indist_G.edges())} edges")

    # Add labels to nodes and edges for DOT export
    for fp in indist_G.nodes():
        indist_G.nodes[fp]["label"] = state_label(filtered_states[fp])
    for u, v, data in indist_G.edges(data=True):
        indist_G.edges[u, v]["label"] = ",".join(data["agents"])

    indist_G.graph["graph"] = {"overlap": "false"}

    dot_path = THIS_DIR / "MuddyChildren-indistinguishability.dot"
    write_dot(indist_G, dot_path)
    print(f"Wrote {dot_path}")

    pdf_path = THIS_DIR / "MuddyChildren-indistinguishability.pdf"
    subprocess.check_call(["neato", "-Tpdf", dot_path, "-o", pdf_path])
    print(f"Wrote {pdf_path}")
