#!/usr/bin/env python3
"""Knowledge analysis for MuddyChildren spec.

MuddyChildren doesn't fit the process-local-variable pattern: the agents are
children 1..N but the only PlusCal process is a controller (AskLoop = 0).
Agent IDs and local state are defined manually here.
"""
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from networkx.drawing.nx_pydot import write_dot

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib import tlc, kripke, formulas

_PALETTE = ["red", "blue", "darkgreen", "purple", "orange", "brown", "cyan", "magenta"]


def _assign_colors(agents):
    return {a: _PALETTE[i % len(_PALETTE)] for i, a in enumerate(agents)}


def _html_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

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
    # Include controller pc so Ask/Answer phases are distinguishable.
    # The father asking is a public event all children observe.
    result.append(state["pc"]["0"])
    return tuple(result)


def phase(state):
    """Return the controller phase: 'Ask' or 'Answer'."""
    return state["pc"]["0"]


def state_label(state: dict) -> str:
    muddy = state["muddy"]
    q = state["q"]
    saidYes = state["saidYes"]
    muddy_str = ",".join(str(i + 1) for i, v in enumerate(muddy) if v) or "none"
    first_said_yes = saidYes[0] if saidYes else []
    yes_str = ",".join(str(i) for i in sorted(first_said_yes)) or "none"
    q_val = q[0] if q else 0
    if phase(state) == "Answer":
        return f"muddy:{muddy_str}\nq={q_val}?"
    return f"muddy:{muddy_str}\nyes:{yes_str} q={q_val}"


def num_muddy(state):
    return sum(1 for v in state["muddy"] if v)


def grid_col(state):
    """Compute grid column index for the two-step layout."""
    q_val = state["q"][0] if state["q"] else 0
    if q_val == 0:
        return 0
    if phase(state) == "Answer":
        return 2 * q_val - 1
    return 2 * q_val


if __name__ == "__main__":
    tlc.run(THIS_DIR / "MuddyChildren.tla")
    G, node_map, edge_actions = tlc.parse_state_graph(THIS_DIR / "MuddyChildren")
    print(f"TLC state graph: {len(G.nodes())} nodes, {len(G.edges())} edges")

    filtered_states = {fp: val for fp, val in node_map.items() if val["pc"]["0"] != "Done"}
    print(f"States (excluding Done): {len(filtered_states)}")

    agents = get_agents(node_map)
    N = len(agents)

    kripke.validate_state_transitions(G, filtered_states, agents, local_state_fn)
    eq_classes = kripke.build_equivalence_classes(filtered_states, agents, local_state_fn)
    indist_G, agents = kripke.build_indistinguishability_graph(filtered_states, eq_classes)
    print(f"Agents: {agents}")
    print(f"Indistinguishability graph: {len(indist_G.nodes())} nodes, {len(indist_G.edges())} edges")

    col_spacing = 1.3
    row_spacing = 0.8

    for fp in indist_G.nodes():
        state = filtered_states[fp]
        label = _html_escape(state_label(state)).replace("\n", "<BR/>")
        indist_G.nodes[fp]["label"] = label
        k = num_muddy(state)
        col = grid_col(state)
        indist_G.nodes[fp]["pos"] = f"{col * col_spacing},{-(k - 1) * row_spacing}!"
        indist_G.nodes[fp]["penwidth"] = "2"
        indist_G.nodes[fp]["fontsize"] = "14"
    agent_colors = _assign_colors(agents)
    edge_labels = {}
    for u, v, data in indist_G.edges(data=True):
        agent_list = data["agents"]
        edge_labels[(u, v)] = (agent_list, agent_colors[agent_list[0]])
        indist_G.edges[u, v]["color"] = ":".join(agent_colors[a] for a in agent_list)
        indist_G.edges[u, v]["penwidth"] = "2"

    indist_G.graph["graph"] = {"overlap": "false", "splines": "curved",
                                "outputorder": "edgesfirst", "margin": "0",
                                "forcelabels": "true"}
    indist_G.graph["node"] = {"shape": "box", "style": "filled", "fillcolor": "white"}

    dot_path = THIS_DIR / "MuddyChildren-indistinguishability.dot"
    write_dot(indist_G, dot_path)

    # Convert quoted labels to HTML labels
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

    # Inject edge label nodes positioned beside each edge
    label_nodes = []
    for i, ((u, v), (agent_list, color)) in enumerate(edge_labels.items()):
        text = ",".join(agent_list)
        su, sv = filtered_states[u], filtered_states[v]
        ku, kv = num_muddy(su), num_muddy(sv)
        col_u = grid_col(su)
        mid_x = col_u * col_spacing - 0.25
        mid_y = -((ku - 1) * row_spacing + (kv - 1) * row_spacing) / 2
        label_nodes.append(
            f'elabel{i} [shape=none, margin=0, fontsize=18, fontcolor="{color}", '
            f'label=<{text}>, pos="{mid_x},{mid_y}!"];\n')

    # Inject legend (position below the grid)
    max_k = max(num_muddy(filtered_states[fp]) for fp in indist_G.nodes())
    legend_y = -(max_k - 1) * row_spacing - 0.7
    cells = "".join(
        f'<TD>&nbsp;</TD><TD BGCOLOR="{agent_colors[a]}" WIDTH="30" HEIGHT="6"></TD>'
        f'<TD>&nbsp;<FONT POINT-SIZE="14">{a}</FONT>&nbsp;</TD>'
        for a in agents
    )
    legend = (f'legend [shape=none, margin=0, pos="0,{legend_y}!", '
              f'label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="4">'
              f'<TR>{cells}</TR></TABLE>>];\n')

    dot_text = dot_text.rstrip().rstrip("}") + "".join(label_nodes) + legend + "}\n"
    dot_path.write_text(dot_text)
    print(f"Wrote {dot_path}")

    pdf_path = THIS_DIR / "MuddyChildren-indistinguishability.pdf"
    subprocess.check_call(["neato", "-n", "-Tpdf", dot_path, "-o", pdf_path])
    print(f"Wrote {pdf_path}")

    # Knowledge analysis: when do muddy children learn they are muddy?
    # Group by (k, q, phase) to show knowledge at each step.

    by_kqp = defaultdict(list)
    for fp, state in filtered_states.items():
        q_val = state["q"][0] if state["q"] else 0
        by_kqp[(num_muddy(state), q_val, phase(state))].append(fp)

    max_q = max(q for _, q, _ in by_kqp)

    knows_muddy = {}
    for agent in agents:
        i = int(agent)
        knows_muddy[agent] = kripke.eval_formula(
            formulas.K(i, formulas.Var("muddy", i)), filtered_states, eq_classes)

    def _check_know(fps, states):
        return fps and all(
            fp in knows_muddy[str(idx + 1)]
            for fp in fps
            for idx, is_m in enumerate(states[fp]["muddy"]) if is_m)

    # Build column headers: q=0, q=1?, q=1, q=2?, q=2, q=3?
    col_headers = ["q=0"]
    for q_val in range(1, max_q + 1):
        col_headers.append(f"q={q_val}?")
        col_headers.append(f"q={q_val}")
    header = "  ".join(f"{h:>5}" for h in col_headers)

    print(f"\nK(i, muddy[i]): does muddy child i know they're muddy? (N={N})")
    print(f"  (q=N? = father asked, q=N = children answered)")
    print()
    print(f"    {header}")

    all_match = True
    for k in range(1, N + 1):
        row = []
        # q=0 (initial, pc=Ask)
        fps = by_kqp.get((k, 0, "Ask"), [])
        row.append("K" if _check_know(fps, filtered_states) else "-")
        for q_val in range(1, max_q + 1):
            # Asked (pc=Answer)
            fps = by_kqp.get((k, q_val, "Answer"), [])
            row.append("K" if _check_know(fps, filtered_states) else "-")
            # Answered (pc=Ask)
            fps = by_kqp.get((k, q_val, "Ask"), [])
            row.append("K" if _check_know(fps, filtered_states) else "-")

        # SaysYes fires at the Answer phase when q = |seesMuddy| + 1 = k
        says_yes_q = k
        first_know_answer = None
        for q_val in range(1, max_q + 1):
            col_idx = 2 * q_val - 1  # index into row for Answer phase
            if row[col_idx] == "K":
                first_know_answer = q_val
                break

        if first_know_answer != says_yes_q:
            all_match = False
        print(f"k={k}  {'  '.join(f'{v:>5}' for v in row)}  (says yes at q={says_yes_q}? phase)")

    print()
    if all_match:
        print("Verified: muddy children know exactly when the algorithm says 'yes'.")
    else:
        print("MISMATCH between algorithm and knowledge!")
