"""Kripke structure: equivalence classes, indistinguishability graph, evaluation."""
from collections import defaultdict

import networkx as nx


def validate_state_transitions(G: nx.DiGraph, node_map: dict, agents: list[str],
                               local_state_fn):
    """Assert every transition changes at least one agent's local state.

    PlusCal generates a 'pc' variable for control flow. If a labeled step only
    changes pc without changing any agent-visible variable, the
    indistinguishability graph will have multiple nodes with the same label.
    Merge such steps with adjacent ones so each atomic step is observable.
    """
    for u, v in G.edges():
        if u == v or u not in node_map or v not in node_map:
            continue
        su, sv = node_map[u], node_map[v]
        if all(local_state_fn(su, a) == local_state_fn(sv, a) for a in agents):
            pc_u = su.get("pc", {})
            pc_v = sv.get("pc", {})
            raise AssertionError(
                f"Transition changes no agent's local state.\n"
                f"  pc before: {pc_u}\n"
                f"  pc after:  {pc_v}\n"
                f"  Merge the source PlusCal label into the next step so every "
                f"atomic step changes at least one agent-visible variable.\n"
                f"  See docs/writing-specs.md for details."
            )


def build_equivalence_classes(node_map: dict, agents: list[str],
                              local_state_fn) -> dict[str, list[frozenset]]:
    """Compute indistinguishability equivalence classes per agent.

    Args:
        node_map: Maps state fingerprints to state dicts.
        agents: List of agent ID strings.
        local_state_fn: (state_dict, agent_id) -> hashable tuple of agent's observation.

    Returns:
        dict mapping agent ID to list of equivalence classes, where each class
        is a frozenset of state fingerprints.
    """
    result = {}
    for agent in agents:
        groups = defaultdict(list)
        for fp, state in node_map.items():
            local = _to_hashable(local_state_fn(state, agent))
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


def eval_formula(ast, node_map: dict, eq_classes: dict[str, list[frozenset]]) -> set: # type: ignore[return]
    """Evaluate a parsed epistemic formula, returning the set of satisfying states."""
    from lib import formulas

    all_fps = set(node_map.keys())
    agents = sorted(eq_classes.keys())
    match ast:
        case formulas.Var(name, index):
            if index is not None:
                return {fp for fp, s in node_map.items() if _lookup(s[name], index)}
            return {fp for fp, s in node_map.items() if s[name]}
        case formulas.BoolLit(value):
            return all_fps if value else set()
        case formulas.Not(body):
            return all_fps - eval_formula(body, node_map, eq_classes)
        case formulas.And(left, right):
            return eval_formula(left, node_map, eq_classes) & eval_formula(right, node_map, eq_classes)
        case formulas.Or(left, right):
            return eval_formula(left, node_map, eq_classes) | eval_formula(right, node_map, eq_classes)
        case formulas.K(agent, body):
            return eval_k(str(agent), eval_formula(body, node_map, eq_classes), eq_classes)
        case formulas.E(body):
            phi = eval_formula(body, node_map, eq_classes)
            result = all_fps
            for agent in agents:
                result &= eval_k(agent, phi, eq_classes)
            return result
        case formulas.C(body):
            # Fixed-point: C(φ) = E(φ) ∧ E(E(φ)) ∧ ...
            phi = eval_formula(body, node_map, eq_classes)
            result = all_fps
            current = phi
            while True:
                e_current = all_fps
                for agent in agents:
                    e_current &= eval_k(agent, current, eq_classes)
                result &= e_current
                if result == current:
                    return result
                current = result


def _lookup(val, index: int):
    """Look up an index in a dict-or-list state variable.

    TLC serializes functions over 1..N and sequences as 0-indexed Python lists,
    but TLA+ indices are 1-based. Functions over other domains (e.g. {0,1}) are
    serialized as dicts with string keys.
    """
    if isinstance(val, dict):
        return val[str(index)]
    return val[index - 1]


def build_indistinguishability_graph(
    node_map: dict, eq_classes: dict[str, list[frozenset]]
) -> tuple[nx.Graph, list]:
    """Build an indistinguishability graph from TLC states.

    Two states are connected by an edge labeled with agents if those agents have
    the same local state in both. This is the standard Kripke structure for
    epistemic logic.

    Returns:
        (G, agents) where G is an undirected graph with states as nodes and edges labeled with the
        agents who cannot distinguish those states.
    """
    agents = sorted(eq_classes.keys())

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
