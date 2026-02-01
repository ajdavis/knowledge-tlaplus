"""Epistemic logic / knowledge analysis utilities."""
from collections import defaultdict

import networkx as nx


def get_agent_state_vars(node_map: dict) -> list[str]:
    """Extract AGENT_STATES variable names from any state."""
    first_state = next(iter(node_map.values()))
    return list(first_state["AGENT_STATES"])


def get_agents(node_map: dict) -> list:
    """Extract agent IDs from the first variable in AGENT_STATES.

    Handles both TLC serialization formats:
    - Functions over {0, 1, 2} become {"0": ..., "1": ..., "2": ...}
    - Functions over 1..N become [...] (array, 0-indexed)
    """
    first_state = next(iter(node_map.values()))
    agent_state_vars = first_state["AGENT_STATES"]
    first_var = agent_state_vars[0]
    var_val = first_state[first_var]

    if isinstance(var_val, dict):
        return sorted(var_val.keys())
    else:
        return [str(i) for i in range(len(var_val))]


def get_local_state(state: dict, agent: str) -> tuple:
    """Extract local state for an agent from state variables.

    Uses AGENT_STATES from the state to determine which variables to include.
    Each variable must be indexed by agent ID.
    """
    agent_state_vars = state["AGENT_STATES"]
    result = []
    for var in agent_state_vars:
        var_val = state[var]
        if isinstance(var_val, dict):
            result.append(var_val[agent])
        else:
            result.append(var_val[int(agent)])
    return tuple(result)


def build_indistinguishability_graph(node_map: dict) -> tuple[nx.MultiGraph, list]:
    """Build an indistinguishability graph from TLC states.

    Two states are connected by an edge labeled with agent if that agent has the
    same local state in both. This is the standard Kripke structure for epistemic
    logic.

    Requires states to have an AGENT_STATES variable listing variable names,
    where each listed variable is indexed by agent ID.

    Args:
        node_map: Maps state fingerprints to state values (from tlc.parse_state_graph)

    Returns:
        (G, agents) where G is an undirected multigraph with state fingerprints as
        nodes and edges labeled with the agent who cannot distinguish those states.
    """
    agents = get_agents(node_map)

    G = nx.MultiGraph()
    G.add_nodes_from(node_map.keys())

    for agent in agents:
        groups = defaultdict(list)
        for fp, state in node_map.items():
            local = get_local_state(state, agent)
            local = _to_hashable(local)
            groups[local].append(fp)

        for fps in groups.values():
            for i, fp1 in enumerate(fps):
                for fp2 in fps[i + 1:]:
                    G.add_edge(fp1, fp2, agent=agent)

    return G, agents


def _to_hashable(val):
    """Convert value to hashable Python type."""
    if isinstance(val, dict):
        return tuple(sorted((k, _to_hashable(v)) for k, v in val.items()))
    elif isinstance(val, list):
        return tuple(_to_hashable(v) for v in val)
    elif isinstance(val, tuple):
        return tuple(_to_hashable(v) for v in val)
    elif isinstance(val, set):
        return frozenset(_to_hashable(v) for v in val)
    else:
        return val
