#!/usr/bin/env python3
"""Knowledge analysis for SimpleRaft spec."""
import subprocess
import sys
from pathlib import Path

from networkx.drawing.nx_pydot import write_dot

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib import tlc, kripke, formulas, pcal

THIS_DIR = Path(__file__).parent


def state_label(state: dict) -> str:
    sent, acks, received = state["sent"], state["acks"], state["received"]
    def fmt(arr):
        return ",".join(str(i + 1) for i, v in enumerate(arr) if v) or "-"
    return f"s:{fmt(sent)} r:{fmt(received)} a:{fmt(acks)}"


if __name__ == "__main__":
    tlc.run(THIS_DIR / "SimpleRaft.tla")
    G, node_map, _ = tlc.parse_state_graph(THIS_DIR / "SimpleRaft")
    print(f"TLC state graph: {len(G.nodes())} nodes, {len(G.edges())} edges")

    processes = pcal.parse_processes(THIS_DIR / "SimpleRaft.tla")
    agents = pcal.get_agents(node_map)
    agent_map = pcal.map_agents_to_processes(processes, node_map)

    def local_state_fn(state, agent):
        return pcal.get_local_state(state, agent, agent_map)

    kripke.validate_state_transitions(G, node_map, agents, local_state_fn)
    eq_classes = kripke.build_equivalence_classes(node_map, agents, local_state_fn)
    indist_G, agents = kripke.build_indistinguishability_graph(node_map, eq_classes)
    print(f"Agents: {agents}")
    print(f"Indistinguishability graph: {len(indist_G.nodes())} nodes, {len(indist_G.edges())} edges")

    # "Leader knows that follower 1 or 2 knows the log entry"
    psi = formulas.parse(r"K(0, K(1, received[1]) \/ K(2, received[2]))")
    psi_states = kripke.eval_formula(psi, node_map, eq_classes)

    print(f"\u03c8 = {psi} holds at {len(psi_states)} states:")
    for fp in psi_states:
        print(f"  {state_label(node_map[fp])}")

    AGENT_COLORS = {"0": "red", "1": "blue", "2": "darkgreen"}

    for fp in indist_G.nodes():
        label = state_label(node_map[fp])
        if fp in psi_states:
            label += "\n\u03c8"
            indist_G.nodes[fp]["style"] = "filled"
            indist_G.nodes[fp]["fillcolor"] = "yellow"
        indist_G.nodes[fp]["label"] = label
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
