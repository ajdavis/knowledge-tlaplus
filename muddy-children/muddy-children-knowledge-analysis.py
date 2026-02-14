#!/usr/bin/env python3
"""Knowledge analysis for MuddyChildren spec.

MuddyChildren doesn't fit the process-local-variable pattern: the agents are
children 1..N but the only PlusCal process is a controller (AskLoop = 0).
Agent IDs and local state are defined manually here.
"""
import subprocess
import sys
from pathlib import Path

from networkx.drawing.nx_pydot import write_dot

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib import tlc, kripke

THIS_DIR = Path(__file__).parent

AGENT_VARS = ["seesMuddy", "saidYes", "m", "q"]


def get_agents(node_map):
    first_state = next(iter(node_map.values()))
    val = first_state[AGENT_VARS[0]]
    if isinstance(val, dict):
        return sorted(val.keys())
    return [str(i + 1) for i in range(len(val))]


def local_state_fn(state, agent):
    result = []
    for var in AGENT_VARS:
        val = state[var]
        if isinstance(val, dict):
            result.append(val[agent])
        else:
            result.append(val[int(agent) - 1])
    return tuple(result)


def state_label(state: dict) -> str:
    muddy = state["muddy"]
    q = state["q"]
    saidYes = state["saidYes"]
    muddy_str = ",".join(str(i + 1) for i, v in enumerate(muddy) if v) or "none"
    first_said_yes = saidYes[0] if saidYes else []
    yes_str = ",".join(str(i) for i in sorted(first_said_yes)) or "none"
    q_val = q[0] if q else 0
    return f"muddy:{muddy_str} yes:{yes_str} q={q_val}"


if __name__ == "__main__":
    tlc.run(THIS_DIR / "MuddyChildren.tla")
    G, node_map, edge_actions = tlc.parse_state_graph(THIS_DIR / "MuddyChildren")
    print(f"TLC state graph: {len(G.nodes())} nodes, {len(G.edges())} edges")

    # Filter out "Done" states
    filtered_states = {fp: val for fp, val in node_map.items() if val["pc"]["0"] != "Done"}
    print(f"States (excluding Done): {len(filtered_states)}")

    agents = get_agents(node_map)
    kripke.validate_state_transitions(G, filtered_states, agents, local_state_fn)

    eq_classes = kripke.build_equivalence_classes(filtered_states, agents, local_state_fn)
    indist_G, agents = kripke.build_indistinguishability_graph(filtered_states, eq_classes)
    print(f"Agents: {agents}")
    print(f"Indistinguishability graph: {len(indist_G.nodes())} nodes, {len(indist_G.edges())} edges")

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
