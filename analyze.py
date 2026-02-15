#!/usr/bin/env python3
"""Generic epistemic analysis tool for PlusCal specs."""
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from networkx.drawing.nx_pydot import write_dot

from lib import tlc, kripke, formulas, pcal
from lib.kripke import _to_hashable


def all_done(state):
    """True if every process is in Done state."""
    pc = state["pc"]
    if isinstance(pc, dict):
        return all(v == "Done" for v in pc.values())
    return all(v == "Done" for v in pc)


def collapse_states(node_map, agents, local_state_fn):
    """Deduplicate states that have identical local state for all agents.

    PlusCal termination steps (e.g. Skip->Done) create states with different pc
    but identical agent-observable state. Keep one representative per unique
    local-state tuple.
    """
    groups = defaultdict(list)
    for fp, state in node_map.items():
        key = tuple(_to_hashable(local_state_fn(state, a)) for a in agents)
        groups[key].append(fp)
    return {fps[0]: node_map[fps[0]] for fps in groups.values()}


def state_label(state):
    """Generic label: all state variables except pc."""
    parts = []
    for k, v in sorted(state.items()):
        if k == "pc":
            continue
        parts.append(f"{k}={v}")
    return "\n".join(parts)


def main(tla_path):
    tla_path = Path(tla_path)
    spec_name = tla_path.stem
    spec_dir = tla_path.parent
    properties = formulas.extract_properties(tla_path)

    tlc.run(tla_path)
    G, node_map, _ = tlc.parse_state_graph(spec_dir / spec_name)
    print(f"TLC state graph: {len(G.nodes())} nodes, {len(G.edges())} edges")

    processes = pcal.parse_processes(tla_path)
    agents = pcal.get_agents(node_map)
    agent_map = pcal.map_agents_to_processes(processes, node_map)

    def local_state_fn(state, agent):
        return pcal.get_local_state(state, agent, agent_map)

    # Filter out terminal states and validate
    filtered = {fp: s for fp, s in node_map.items() if not all_done(s)}
    if len(filtered) < len(node_map):
        print(f"States (excluding Done): {len(filtered)}")
    else:
        filtered = node_map

    kripke.validate_state_transitions(G, filtered, agents, local_state_fn)

    # Collapse states that differ only in pc
    states = collapse_states(filtered, agents, local_state_fn)
    if len(states) < len(filtered):
        print(f"States (after collapsing): {len(states)}")

    eq_classes = kripke.build_equivalence_classes(states, agents, local_state_fn)
    indist_G, agents = kripke.build_indistinguishability_graph(states, eq_classes)
    print(f"Agents: {agents}")
    print(f"Indistinguishability graph: {len(indist_G.nodes())} nodes, "
          f"{len(indist_G.edges())} edges")

    # Evaluate properties
    sat_states = set()
    for prop_text in properties:
        ast = formulas.parse(prop_text)
        result = kripke.eval_formula(ast, states, eq_classes)
        sat_states |= result
        print(f"\n{ast} holds at {len(result)}/{len(states)} states:")
        for fp in sorted(result):
            print(f"  {state_label(states[fp])}")

    # Build DOT graph
    for fp in indist_G.nodes():
        label = state_label(states[fp])
        if fp in sat_states:
            indist_G.nodes[fp]["style"] = "filled"
            indist_G.nodes[fp]["fillcolor"] = "yellow"
        indist_G.nodes[fp]["label"] = label
    for u, v, data in indist_G.edges(data=True):
        indist_G.edges[u, v]["label"] = ",".join(data["agents"])

    indist_G.graph["graph"] = {"overlap": "false"}

    dot_path = spec_dir / f"{spec_name}-indistinguishability.dot"
    write_dot(indist_G, dot_path)
    print(f"\nWrote {dot_path}")

    pdf_path = spec_dir / f"{spec_name}-indistinguishability.pdf"
    subprocess.check_call(["neato", "-Tpdf", dot_path, "-o", pdf_path])
    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main(sys.argv[1])
