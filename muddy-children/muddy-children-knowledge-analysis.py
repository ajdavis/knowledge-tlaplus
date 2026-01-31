import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib import tlc

THIS_DIR = Path(__file__).parent

if __name__ == "__main__":
    tlc.run(THIS_DIR / "MuddyChildren.tla")
    G, node_map, edge_actions = tlc.parse_state_graph(THIS_DIR / "MuddyChildren")
    print(f"{len(G.nodes())} nodes, {len(G.edges())} edges")
