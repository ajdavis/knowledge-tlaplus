"""Test that specs with pc-only transitions are rejected."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib import tlc, kripke, pcal

THIS_DIR = Path(__file__).parent


def _local_state(state, agent):
    x = state["x"]
    if isinstance(x, dict):
        return (x[agent],)
    return (x[int(agent) - 1],)


def test_pc_only_transition_rejected():
    tlc.run(THIS_DIR / "BadSpec.tla")
    G, node_map, _ = tlc.parse_state_graph(THIS_DIR / "BadSpec")
    agents = pcal.get_agents(node_map)
    with pytest.raises(AssertionError, match="changes no agent's local state"):
        kripke.validate_state_transitions(G, node_map, agents, _local_state)
