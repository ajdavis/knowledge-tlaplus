#!/usr/bin/env python3
"""Generic epistemic analysis tool for PlusCal specs."""
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import networkx as nx
from networkx.drawing.nx_pydot import write_dot

from lib import tlc, kripke, formulas, pcal
from lib.kripke import _to_hashable


def collapse_states(node_map, agents, local_state_fn):
    """Deduplicate states that have identical local state for all agents.

    PlusCal termination steps (e.g. Skip->Done) create states with different pc
    but identical agent-observable state. Keep one representative per unique
    local-state tuple.

    Returns (collapsed_node_map, collapse_map) where collapse_map maps every
    original fingerprint to its collapsed representative.
    """
    groups = defaultdict(list)
    for fp, state in node_map.items():
        key = tuple(_to_hashable(local_state_fn(state, a)) for a in agents)
        groups[key].append(fp)
    collapsed = {fps[0]: node_map[fps[0]] for fps in groups.values()}
    collapse_map = {fp: fps[0] for fps in groups.values() for fp in fps}
    return collapsed, collapse_map


def collapse_graph(G, collapse_map):
    """Project a directed graph through a collapse mapping."""
    CG = nx.DiGraph()
    CG.add_nodes_from(set(collapse_map.values()))
    for u, v in G.edges():
        cu, cv = collapse_map.get(u), collapse_map.get(v)
        if cu is not None and cv is not None and cu != cv:
            CG.add_edge(cu, cv)
    return CG


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


def _check_property(ast, states, eq_classes, collapsed_G, all_fps, label_kwargs):
    """Check a temporal property. Returns True if it passes."""
    match ast:
        case formulas.Always(body):
            result = kripke.eval_formula(body, states, eq_classes, G=collapsed_G)
            passed, violations = kripke.check_always(result, all_fps)
            if passed:
                print(f"\n{ast}: PASS (holds at all {len(all_fps)} states)")
            else:
                print(f"\n{ast}: FAIL ({len(violations)} violating states):")
                for fp in sorted(violations):
                    print(f"  {state_label(states[fp], **label_kwargs)}")
            return passed
        case formulas.Eventually(body):
            result = kripke.eval_formula(body, states, eq_classes, G=collapsed_G)
            passed, violations = kripke.check_eventually(collapsed_G, result)
            if passed:
                print(f"\n{ast}: PASS")
            else:
                print(f"\n{ast}: FAIL ({len(violations)} initial states "
                      f"can avoid {body}):")
                for fp in sorted(violations):
                    print(f"  {state_label(states[fp], **label_kwargs)}")
            return passed
        case formulas.LeadsTo(left, right):
            psi = kripke.eval_formula(left, states, eq_classes, G=collapsed_G)
            phi = kripke.eval_formula(right, states, eq_classes, G=collapsed_G)
            passed, violations = kripke.check_leads_to(collapsed_G, psi, phi)
            if passed:
                print(f"\n{ast}: PASS")
            else:
                print(f"\n{ast}: FAIL ({len(violations)} states where "
                      f"{left} holds but {right} is not inevitable):")
                for fp in sorted(violations):
                    print(f"  {state_label(states[fp], **label_kwargs)}")
            return passed
        case _:
            raise ValueError(f"KNOWLEDGE_PROPERTY requires a temporal operator "
                             f"([], <>, ~>), got: {ast}")


def _states_at_label(label, node_map, collapse_map):
    """Find collapsed states where some agent's pc matches label."""
    collapsed = set()
    for fp, state in node_map.items():
        pc = state.get("pc", {})
        if any(v == label for v in (pc.values() if isinstance(pc, dict) else pc)):
            collapsed.add(collapse_map[fp])
    return collapsed


def _check_precondition(label, ast, node_map, collapse_map, states, eq_classes,
                        collapsed_G, label_kwargs):
    """Check that a knowledge formula holds at all states with the given pc label."""
    labeled = _states_at_label(label, node_map, collapse_map)
    sat = kripke.eval_formula(ast, states, eq_classes, G=collapsed_G)
    violations = labeled - sat
    if not violations:
        print(f"\nPrecondition {label}: {ast}: PASS "
              f"(holds at all {len(labeled)} states)")
        return True
    print(f"\nPrecondition {label}: {ast}: FAIL "
          f"({len(violations)} violating states):")
    for fp in sorted(violations):
        print(f"  {state_label(states[fp], **label_kwargs)}")
    return False


def main(tla_path):
    tla_path = Path(tla_path)
    spec_name = tla_path.stem
    spec_dir = tla_path.parent
    queries = formulas.extract_queries(tla_path)
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

    kripke.validate_state_transitions(G, node_map, agents, local_state_fn)

    # Collapse states that differ only in pc (e.g. Skip→Done in CardGame)
    states, collapse_map = collapse_states(node_map, agents, local_state_fn)
    if len(states) < len(node_map):
        print(f"States (after collapsing): {len(states)}")

    eq_classes = kripke.build_equivalence_classes(states, agents, local_state_fn)
    indist_G, agents = kripke.build_indistinguishability_graph(states, eq_classes)
    print(f"Agents: {agents}")
    print(f"Indistinguishability graph: {len(indist_G.nodes())} nodes, "
          f"{len(indist_G.edges())} edges")

    # Build collapsed directed graph for temporal checks
    collapsed_G = collapse_graph(G, collapse_map)

    label_kwargs = dict(template=node_label_template, processes=processes,
                        agent_map=agent_map)
    all_fps = set(states.keys())

    # Evaluate queries (exploratory, per-state)
    sat_states = {}  # fp -> list of HTML formula strings
    for q in queries:
        ast = formulas.parse(q.formula)
        result = kripke.eval_formula(ast, states, eq_classes, G=collapsed_G)
        html = formulas.to_html(ast)
        print(f"\n{ast} holds at {len(result)}/{len(all_fps)} states:")
        for fp in sorted(result):
            print(f"  {state_label(states[fp], **label_kwargs)}")
            sat_states.setdefault(fp, [])
            sat_states[fp].append(html)

    # Check properties (temporal assertions)
    all_passed = True
    for prop in properties:
        ast = formulas.parse(prop.formula)
        if not _check_property(ast, states, eq_classes, collapsed_G, all_fps,
                               label_kwargs):
            all_passed = False

    # Check preconditions (knowledge at specific labels)
    preconditions = formulas.extract_preconditions(tla_path)
    for pre in preconditions:
        ast = formulas.parse(pre.formula)
        if not _check_precondition(pre.alias, ast, node_map, collapse_map,
                                   states, eq_classes, collapsed_G, label_kwargs):
            all_passed = False

    # Build DOT graph
    def _html_escape(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    for fp in indist_G.nodes():
        label = _html_escape(state_label(states[fp], **label_kwargs))
        label = label.replace("\n", '<BR/>')
        if fp in sat_states:
            for html in sat_states[fp]:
                label += '<BR/>' + html
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

    # Convert quoted labels to HTML labels (write_dot only emits quoted labels)
    dot_text = dot_path.read_text()
    dot_text = re.sub(
        r'label="((?:[^"\\]|\\.)*)"',
        lambda m: (
            'label=<<TABLE BORDER="0" CELLPADDING="0" CELLSPACING="0">'
            '<TR><TD BALIGN="LEFT">'
            + m.group(1).replace('\\"', '"')
            + '<BR/></TD></TR></TABLE>>'
        ),
        dot_text)
    dot_path.write_text(dot_text)

    # Inject HTML legend node
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

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1])
