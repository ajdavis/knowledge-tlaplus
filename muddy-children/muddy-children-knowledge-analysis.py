import subprocess
import sys
from pathlib import Path

from networkx.drawing.nx_pydot import write_dot

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib import tlc, knowledge

THIS_DIR = Path(__file__).parent


def local_state(state_val: dict, agent: int) -> tuple:
    """What child 'agent' can see: other muddy children, who has said yes, m, and q."""
    muddy = state_val["muddy"]
    m = state_val["m"]
    q = state_val["q"]
    saidYes = state_val["saidYes"]
    # Set of muddy children that agent can see (everyone except themselves)
    sees_muddy = frozenset(i for i, is_muddy in enumerate(muddy, 1) if i != agent and is_muddy)
    # Who has said yes (visible to all)
    said_yes = frozenset(i for i, said in enumerate(saidYes, 1) if said)
    return (sees_muddy, said_yes, m, q)


def state_label(state: dict) -> str:
    """Create a human-readable label for a state."""
    muddy = state["muddy"]
    q = state["q"]
    saidYes = state["saidYes"]
    muddy_str = ",".join(str(i) for i, v in enumerate(muddy, 1) if v) or "none"
    yes_str = ",".join(str(i) for i, v in enumerate(saidYes, 1) if v) or "none"
    return f"muddy:{muddy_str} yes:{yes_str} q={q}"


if __name__ == "__main__":
    tlc.run(THIS_DIR / "MuddyChildren.tla")
    G, node_map, edge_actions = tlc.parse_state_graph(THIS_DIR / "MuddyChildren")
    print(f"TLC state graph: {len(G.nodes())} nodes, {len(G.edges())} edges")

    # The "Done" states are not interesting in this spec.
    filtered_states = {fp: val for fp, val in node_map.items() if val["pc"]["0"] != "Done"}
    print(f"States: {len(filtered_states)}")

    # Number of children == size of "muddy" array.
    n = len(filtered_states[next(iter(filtered_states))]["muddy"])

    children = list(range(1, n + 1))
    indist_G = knowledge.build_indistinguishability_graph(filtered_states, children, local_state)
    print(f"Indistinguishability graph: {len(indist_G.nodes())} nodes, {len(indist_G.edges())} edges")

    # Add labels to nodes and edges for DOT export
    for fp in indist_G.nodes():
        indist_G.nodes[fp]["label"] = state_label(filtered_states[fp])
    for u, v, key, data in indist_G.edges(keys=True, data=True):
        indist_G.edges[u, v, key]["label"] = str(data["agent"])

    # Set graph attributes for layout
    indist_G.graph["graph"] = {"overlap": False}

    dot_path = THIS_DIR / "MuddyChildren-indistinguishability.dot"
    write_dot(indist_G, dot_path)
    print(f"Wrote {dot_path}")

    pdf_path = THIS_DIR / "MuddyChildren-indistinguishability.pdf"
    subprocess.check_call(["neato", "-Tpdf", dot_path, "-o", pdf_path])
    print(f"Wrote {pdf_path}")
