from collections import defaultdict
from typing import Callable

import networkx as nx


def build_indistinguishability_graph(
    node_map: dict,
    agents: list,
    local_state: Callable[[dict, any], any],
) -> nx.Graph:
    """Build an indistinguishability graph from TLC states.

    Two states are connected by an edge labeled with agent if that agent has the
    same local state in both. This is the standard Kripke structure for epistemic
    logic.

    Args:
        node_map: Maps state fingerprints to state values (from tlc.parse_state_graph)
        agents: List of agent identifiers
        local_state: Function (state_val, agent) -> hashable local state for that agent

    Returns:
        Undirected multigraph where nodes are state fingerprints and edges are
        labeled with the agent who cannot distinguish those states.
    """
    G = nx.MultiGraph()
    G.add_nodes_from(node_map.keys())

    for agent in agents:
        groups = defaultdict(list)
        for fp, state_val in node_map.items():
            local = local_state(state_val, agent)
            groups[local].append(fp)

        for fps in groups.values():
            for i, fp1 in enumerate(fps):
                for fp2 in fps[i + 1:]:
                    G.add_edge(fp1, fp2, agent=agent)

    return G
