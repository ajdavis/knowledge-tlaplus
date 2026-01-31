"""
This is exploratory, it doesn't use TLA+ or PlusCal.
"""

import copy
import subprocess
from dataclasses import field, dataclass

NODE_COUNT = 3


@dataclass(unsafe_hash=True)
class Node:
    node_id: int
    node_has_w: tuple[bool, ...] = field(
        default_factory=lambda: tuple(False for _ in range(NODE_COUNT)))
    """Whether each node has acknowledged w, to my knowledge."""
    w_committed: bool = False

    def __post_init__(self):
        assert self.node_id < NODE_COUNT
        assert len(self.node_has_w) == NODE_COUNT

    def node_acked_w(self, node_id: int) -> None:
        assert node_id < NODE_COUNT
        self.node_has_w = tuple(
            True if i == node_id else self.node_has_w[i]
            for i in range(NODE_COUNT))

    def set_has_w(self):
        self.node_acked_w(self.node_id)

    @property
    def has_w(self):
        return self.node_has_w[self.node_id]


@dataclass(unsafe_hash=True)
class State:
    name: str
    nodes: tuple[Node, ...]

    def __post_init__(self):
        assert len(self.nodes) == NODE_COUNT


states: list[State] = []
state_transitions: dict[State, State] = {}

init = State("init", tuple(Node(i) for i in range(NODE_COUNT)))
states.append(init)

# Client sends w to Node 0, the leader.
write_received = copy.deepcopy(init)
write_received.name = "write received"
write_received.nodes[0].set_has_w()
states.append(write_received)
state_transitions[init] = write_received

# Node 0 sends w to Node 1, a follower.
replicated_once = copy.deepcopy(write_received)
replicated_once.name = "replicated once"
replicated_once.nodes[1].set_has_w()
states.append(replicated_once)
state_transitions[write_received] = replicated_once

# Node 1 acknowledges w to Node 0.
acked_once = copy.deepcopy(replicated_once)
acked_once.name = "acked once"
acked_once.nodes[0].node_acked_w(1)
acked_once.nodes[0].w_committed = True
states.append(acked_once)
state_transitions[replicated_once] = acked_once

# Node 0 tells Node 1 that w is committed.
committed_on_1 = copy.deepcopy(acked_once)
committed_on_1.name = "committed on node 1"
committed_on_1.nodes[1].w_committed = True
states.append(committed_on_1)
state_transitions[acked_once] = committed_on_1

# Node 0 sends w to Node 2.
replicated_twice = copy.deepcopy(committed_on_1)
replicated_twice.name = "replicated twice"
replicated_twice.nodes[2].set_has_w()
states.append(replicated_twice)
state_transitions[committed_on_1] = replicated_twice

# Node 2 acknowledges w to Node 0.
acked_twice = copy.deepcopy(replicated_twice)
acked_twice.name = "acked twice"
acked_twice.nodes[0].node_acked_w(2)
states.append(acked_twice)
state_transitions[replicated_twice] = acked_twice

# Node 0 tells Node 2 that w is committed.
committed_on_2 = copy.deepcopy(acked_twice)
committed_on_2.name = "committed on node 2"
committed_on_2.nodes[2].w_committed = True
states.append(committed_on_2)
state_transitions[acked_twice] = committed_on_2


@dataclass(unsafe_hash=True)
class KnowledgeEdge:
    state_a: int
    """Index into states."""
    state_b: int
    """Index into states."""
    node_ids: list[int]
    """Which nodes can't distinguish between state_a and state_b."""


knowledge_edges: list[KnowledgeEdge] = []
for i in range(len(states)):
    for j in range(i + 1, len(states)):
        indistinguishable_to_nodes = [
            k for k in range(NODE_COUNT)
            if states[i].nodes[k] == states[j].nodes[k]]
        if indistinguishable_to_nodes:
            knowledge_edges.append(KnowledgeEdge(i, j, indistinguishable_to_nodes))

with open('knowledge-graph.dot', 'w') as f:
    f.write('digraph {\n')
    f.write('  rankdir=LR;\n')
    for state in states:
        f.write(f'  "{state.name}"\n')

    for source, target in state_transitions.items():
        f.write(f'  "{source.name}" -> "{target.name}"\n')

    for edge in knowledge_edges:
        node_id_strs = [str(i) for i in edge.node_ids]
        f.write(f'  "{states[edge.state_a].name}" -> "{states[edge.state_b].name}"'
                f' [dir=none,color=red,label="{','.join(node_id_strs)}"]\n')
    f.write('}\n')

subprocess.check_call([
    'dot', '-Tpdf', 'knowledge-graph.dot', '-o', 'knowledge-graph.pdf'])
