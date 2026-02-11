#!/usr/bin/env python3
"""Knowledge analysis for SimpleRaft spec."""
import subprocess
import sys
from pathlib import Path

from networkx.drawing.nx_pydot import write_dot

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib import tlc, knowledge

THIS_DIR = Path(__file__).parent


def state_label(state: dict) -> str:
    """Create a human-readable label for a state."""
    r, a = state["r"], state["a"]
    # r and a are indexed by node ID (0, 1, 2)
    r_str = ",".join(k for k, v in sorted(r.items()) if v and k != "0")
    a_acks = a.get("0", [])
    a_str = ",".join(str(i + 1) for i, v in enumerate(a_acks) if v)
    return f"r:{r_str or 'none'} a:{a_str or 'none'}"


if __name__ == "__main__":
    tlc.run(THIS_DIR / "SimpleRaft.tla")
    G, node_map, edge_actions = tlc.parse_state_graph(THIS_DIR / "SimpleRaft")
    print(f"TLC state graph: {len(G.nodes())} nodes, {len(G.edges())} edges")

    indist_G, agents = knowledge.build_indistinguishability_graph(node_map)
    print(f"Agents: {agents}")
    print(f"Indistinguishability graph: {len(indist_G.nodes())} nodes, {len(indist_G.edges())} edges")

    AGENT_COLORS = {"0": "red", "1": "blue", "2": "darkgreen"}

    # Add labels and colors to nodes and edges for DOT export
    for fp in indist_G.nodes():
        indist_G.nodes[fp]["label"] = state_label(node_map[fp])
    for u, v, data in indist_G.edges(data=True):
        agent_list = data["agents"]
        if len(agent_list) == 1:
            indist_G.edges[u, v]["color"] = AGENT_COLORS[agent_list[0]]
        else:
            indist_G.edges[u, v]["color"] = ":".join(
                AGENT_COLORS[a] for a in agent_list
            )

    indist_G.graph["graph"] = {"overlap": "false", "splines": "curved"}

    dot_path = THIS_DIR / "SimpleRaft-indistinguishability.dot"
    write_dot(indist_G, dot_path)

    # Append a legend subgraph
    dot_text = dot_path.read_text()
    legend = """
subgraph cluster_legend {
  label="Agents";
  style=filled;
  fillcolor=white;
  node [shape=plaintext];
  edge [penwidth=2];
  l0a [label=""];
  l0b [label="0"];
  l0a -- l0b [color=red];
  l1a [label=""];
  l1b [label="1"];
  l1a -- l1b [color=blue];
  l2a [label=""];
  l2b [label="2"];
  l2a -- l2b [color=darkgreen];
}
"""
    dot_text = dot_text.rstrip().rstrip("}")
    dot_text += legend + "\n}\n"
    dot_path.write_text(dot_text)
    print(f"Wrote {dot_path}")

    pdf_path = THIS_DIR / "SimpleRaft-indistinguishability.pdf"
    subprocess.check_call(["sfdp", "-Tpdf", dot_path, "-o", pdf_path])
    print(f"Wrote {pdf_path}")
