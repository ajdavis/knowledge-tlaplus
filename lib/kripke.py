"""Kripke structure: equivalence classes, indistinguishability graph, evaluation."""
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
        return [str(i + 1) for i in range(len(var_val))]


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
            result.append(var_val[int(agent) - 1])
    return tuple(result)


def validate_state_transitions(G: nx.DiGraph, node_map: dict):
    """Assert every transition changes at least one AGENT_STATES variable.

    PlusCal generates a 'pc' variable for control flow. If a labeled step only
    changes pc without changing any agent-visible variable, the
    indistinguishability graph will have multiple nodes with the same label.
    Merge such steps with adjacent ones so each atomic step is observable.
    """
    agent_vars = get_agent_state_vars(node_map)
    for u, v in G.edges():
        if u == v or u not in node_map or v not in node_map:
            continue
        su, sv = node_map[u], node_map[v]
        changed = [var for var in agent_vars if su[var] != sv[var]]
        if not changed:
            pc_u = su.get("pc", {})
            pc_v = sv.get("pc", {})
            raise AssertionError(
                f"Transition changes no AGENT_STATES variable ({agent_vars}).\n"
                f"  pc before: {pc_u}\n"
                f"  pc after:  {pc_v}\n"
                f"  Merge the source PlusCal label into the next step so every "
                f"atomic step changes at least one agent-visible variable.\n"
                f"  See docs/writing-specs.md for details."
            )


def build_equivalence_classes(node_map: dict) -> dict[str, list[frozenset]]:
    """Compute indistinguishability equivalence classes per agent.

    Returns:
        dict mapping agent ID to list of equivalence classes, where each class
        is a frozenset of state fingerprints.
    """
    agents = get_agents(node_map)
    result = {}
    for agent in agents:
        groups = defaultdict(list)
        for fp, state in node_map.items():
            local = _to_hashable(get_local_state(state, agent))
            groups[local].append(fp)
        result[agent] = [frozenset(fps) for fps in groups.values()]
    return result


def eval_k(agent: str, phi_states: set, eq_classes: dict[str, list[frozenset]]) -> set:
    """Evaluate K(agent, φ): states where agent knows φ.

    K(agent, φ) holds at state s iff φ holds at all states in s's equivalence
    class for that agent.
    """
    result = set()
    for cls in eq_classes[agent]:
        if cls.issubset(phi_states):
            result.update(cls)
    return result


def build_indistinguishability_graph(
    node_map: dict, eq_classes: dict[str, list[frozenset]]
) -> tuple[nx.Graph, list]:
    """Build an indistinguishability graph from TLC states.

    Two states are connected by an edge labeled with agents if those agents have
    the same local state in both. This is the standard Kripke structure for
    epistemic logic.

    Args:
        node_map: Maps state fingerprints to state values (from tlc.parse_state_graph)
        eq_classes: Equivalence classes from build_equivalence_classes.

    Returns:
        (G, agents) where G is an undirected graph with states as nodes and edges labeled with the
        agents who cannot distinguish those states.
    """
    agents = get_agents(node_map)

    # Build pairwise edges from equivalence classes
    edge_agents = defaultdict(list)
    for agent in agents:
        for cls in eq_classes[agent]:
            fps = sorted(cls)
            for i, fp1 in enumerate(fps):
                for fp2 in fps[i + 1:]:
                    edge_agents[(fp1, fp2)].append(agent)

    G = nx.Graph()
    G.add_nodes_from(node_map.keys())
    for (fp1, fp2), agents_list in edge_agents.items():
        G.add_edge(fp1, fp2, agents=agents_list)

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
