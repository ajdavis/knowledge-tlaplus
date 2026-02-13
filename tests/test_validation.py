"""Test that specs with pc-only transitions are rejected."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib import tlc, kripke

THIS_DIR = Path(__file__).parent


def test_pc_only_transition_rejected():
    tlc.run(THIS_DIR / "BadSpec.tla")
    G, node_map, _ = tlc.parse_state_graph(THIS_DIR / "BadSpec")
    with pytest.raises(AssertionError, match="changes no AGENT_STATES variable"):
        kripke.validate_state_transitions(G, node_map)
