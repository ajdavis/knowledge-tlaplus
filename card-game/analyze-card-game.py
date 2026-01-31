import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib import tlc, knowledge

THIS_DIR = Path(__file__).parent


def local_state(state_val: dict, agent: int) -> str:
    """Agent's local state is the card in their hand."""
    deal = state_val["deal"]
    return deal[agent - 1]  # deal is 1-indexed in TLA+, 0-indexed in JSON


def render_graph(G, node_map, output_path: Path):
    """Write graph to DOT file and render to PDF with graphviz."""
    dot_path = output_path.with_suffix(".dot")

    lines = ["graph G {", "  overlap=false;"]

    for fp in G.nodes():
        deal = node_map[fp]["deal"]
        label = f"1:{deal[0]} 2:{deal[1]} T:{deal[2]}"
        lines.append(f'  "{fp}" [label="{label}"];')

    for u, v, data in G.edges(data=True):
        lines.append(f'  "{u}" -- "{v}" [label="{data["agent"]}"];')

    lines.append("}")

    dot_path.write_text("\n".join(lines))
    subprocess.check_call(["neato", "-Tpdf", dot_path, "-o", output_path])


if __name__ == "__main__":
    tlc.run(THIS_DIR / "CardGame.tla")
    _, node_map, _ = tlc.parse_state_graph(THIS_DIR / "CardGame")

    # Filter to initial states only (pc = "Skip" for both agents)
    initial_states = {
        fp: val for fp, val in node_map.items()
        if val["pc"] == ["Skip", "Skip"]
    }

    G = knowledge.build_indistinguishability_graph(
        initial_states,
        agents=[1, 2],
        local_state=local_state,
    )
    print(f"{len(G.nodes())} states, {len(G.edges())} indistinguishability edges")
    output = THIS_DIR / "CardGame-indistinguishability.pdf"
    render_graph(G, initial_states, output)
    print(f"Wrote {output}")
