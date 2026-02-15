#!/usr/bin/env python3
"""Generic epistemic analysis tool for PlusCal specs."""
import re
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


def state_label(state, template=None, processes=None, agent_map=None):
    """Build node label from state. Uses template if provided, else generic dump."""
    if template is None:
        parts = [f"{k}={v}" for k, v in sorted(state.items()) if k != "pc"]
        return "\n".join(parts)
    context = pcal.build_label_context(state, processes, agent_map)
    rendered = template.replace('\\n', '\n')
    return eval(f'f"""{rendered}"""', context)  # noqa: S307


_PALETTE = ["red", "blue", "darkgreen", "purple", "orange", "brown", "cyan", "magenta"]


def _assign_colors(agents):
    return {a: _PALETTE[i % len(_PALETTE)] for i, a in enumerate(agents)}


def main(tla_path):
    tla_path = Path(tla_path)
    spec_name = tla_path.stem
    spec_dir = tla_path.parent
    properties = formulas.extract_properties(tla_path)
    node_label_template = formulas.extract_node_label(tla_path)

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
    label_kwargs = dict(template=node_label_template, processes=processes,
                        agent_map=agent_map)
    sat_states = {}  # fp -> set of aliases
    for prop in properties:
        ast = formulas.parse(prop.formula)
        result = kripke.eval_formula(ast, states, eq_classes)
        print(f"\n{ast} holds at {len(result)}/{len(states)} states:")
        for fp in sorted(result):
            print(f"  {state_label(states[fp], **label_kwargs)}")
            sat_states.setdefault(fp, set())
            if prop.alias:
                sat_states[fp].add(prop.alias)

    # Build DOT graph
    for fp in indist_G.nodes():
        label = state_label(states[fp], **label_kwargs)
        if fp in sat_states:
            aliases = sat_states[fp]
            if aliases:
                label += "\n" + ", ".join(sorted(aliases))
            indist_G.nodes[fp]["style"] = "filled"
            indist_G.nodes[fp]["fillcolor"] = "yellow"
        indist_G.nodes[fp]["label"] = label
        indist_G.nodes[fp]["penwidth"] = "3"
        indist_G.nodes[fp]["fontsize"] = "24"
    agent_colors = _assign_colors(agents)
    for u, v, data in indist_G.edges(data=True):
        agent_list = data["agents"]
        indist_G.edges[u, v]["color"] = ":".join(agent_colors[a] for a in agent_list)
        indist_G.edges[u, v]["penwidth"] = "3"

    indist_G.graph["graph"] = {"overlap": "false", "splines": "curved",
                                "outputorder": "edgesfirst", "K": "0.1"}
    indist_G.graph["node"] = {"shape": "box", "style": "filled", "fillcolor": "white"}

    dot_path = spec_dir / f"{spec_name}-indistinguishability.dot"
    write_dot(indist_G, dot_path)

    # Inject HTML legend node (write_dot doesn't support HTML labels)
    cells = "".join(
        f'<TD>&nbsp;</TD><TD BGCOLOR="{agent_colors[a]}" WIDTH="30" HEIGHT="6"></TD>'
        f'<TD>&nbsp;<FONT POINT-SIZE="24">{a}</FONT>&nbsp;</TD>'
        for a in agents
    )
    legend = (f'legend [shape=none, margin=0, '
              f'label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="4">'
              f'<TR>{cells}</TR></TABLE>>];\n')
    dot_text = dot_path.read_text()
    dot_path.write_text(dot_text.rstrip().rstrip("}") + legend + "}\n")
    print(f"\nWrote {dot_path}")

    # Layout with neato + scalexy (compact), then scale positions up for readability
    laid_out = subprocess.check_output(
        ["neato", "-Goverlap=scalexy", "-Tdot", dot_path]).decode()

    def _scale_pos(m):
        parts = m.group(1).split()
        scaled = [",".join(str(float(n) * 1.3) for n in p.split(",")) for p in parts]
        return f'pos="{" ".join(scaled)}"'

    laid_out = re.sub(r'pos="([^"]+)"', _scale_pos, laid_out)
    laid_out = re.sub(
        r'bb="([^"]+)"',
        lambda m: 'bb="' + ",".join(str(float(x) * 1.3) for x in m.group(1).split(",")) + '"',
        laid_out)
    dot_path.write_text(laid_out)

    pdf_path = spec_dir / f"{spec_name}-indistinguishability.pdf"
    subprocess.check_call(["neato", "-n", "-Tpdf", dot_path, "-o", pdf_path])
    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main(sys.argv[1])
