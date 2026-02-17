"""Parse PlusCal to extract process declarations and local variables."""
from dataclasses import dataclass, field
from pathlib import Path

import tree_sitter_tlaplus as tstla
from tree_sitter import Language, Parser

_lang = Language(tstla.language())
_parser = Parser(_lang)


@dataclass
class ProcessInfo:
    name: str
    is_set: bool  # True for `\in expr`, False for `= expr`
    first_label: str
    local_vars: list[str] = field(default_factory=list)


def parse_processes(tla_path: str | Path) -> list[ProcessInfo]:
    """Extract process declarations from a PlusCal spec embedded in a .tla file."""
    src = Path(tla_path).read_bytes()
    tree = _parser.parse(src)
    return [_parse_process(node) for node in _find_all(tree.root_node, "pcal_process")]


def _parse_process(node) -> ProcessInfo:
    name = node.child_by_field_name("name").text.decode()
    is_set = any(c.type == "set_in" for c in node.children)

    local_vars = []
    for var_decls in _find_all(node, "pcal_var_decl"):
        # First identifier child is the variable name
        for c in var_decls.children:
            if c.type == "identifier":
                local_vars.append(c.text.decode())
                break

    body = next(c for c in node.children if c.type == "pcal_algorithm_body")
    first_label = next(c for c in body.children if c.type == "identifier").text.decode()

    return ProcessInfo(name=name, is_set=is_set, first_label=first_label, local_vars=local_vars)


def map_agents_to_processes(
    processes: list[ProcessInfo], node_map: dict
) -> dict[str, ProcessInfo]:
    """Map agent IDs to their process using initial pc labels.

    Returns dict mapping agent ID (string) to ProcessInfo.
    """
    first_state = next(iter(node_map.values()))
    pc = first_state["pc"]
    label_to_process = {p.first_label: p for p in processes}
    return {agent_id: label_to_process[label] for agent_id, label in _iter_indexed(pc)}


def get_agents(node_map: dict) -> list[str]:
    """Extract agent IDs from the pc variable in the first state."""
    first_state = next(iter(node_map.values()))
    pc = first_state["pc"]
    return [agent_id for agent_id, _ in _iter_indexed(pc)]


def get_local_state(
    state: dict, agent: str, agent_process_map: dict[str, ProcessInfo]
) -> tuple:
    """Extract an agent's local state based on its process's local variables."""
    proc = agent_process_map[agent]
    result = []
    for var in proc.local_vars:
        val = state[var]
        if proc.is_set:
            # Variable is a function from the process set; index by agent ID
            if isinstance(val, dict):
                result.append(val[agent])
            else:
                result.append(val[int(agent) - 1])
        else:
            # Singleton process: the whole value is the agent's
            result.append(val)
    return tuple(result)


def _iter_indexed(val):
    """Iterate (key, value) pairs for a dict-or-list TLC variable."""
    if isinstance(val, dict):
        for k in sorted(val.keys()):
            yield k, val[k]
    else:
        for i, v in enumerate(val):
            yield str(i + 1), v


def build_label_context(state, processes, agent_map):
    """Build a template context dict from a state.

    All state variables except pc are included. Set-process local vars that are
    lists are converted to dicts keyed by integer agent ID.
    """
    set_vars = {}
    for proc in processes:
        if proc.is_set:
            for var in proc.local_vars:
                set_vars[var] = [aid for aid, p in agent_map.items() if p is proc]
    context = {}
    for key, value in state.items():
        if key == "pc":
            continue
        if key in set_vars and isinstance(value, list):
            agents = set_vars[key]
            context[key] = {int(a): value[i] for i, a in enumerate(agents)}
        elif key in set_vars and isinstance(value, dict):
            context[key] = {int(k): v for k, v in value.items()}
        else:
            context[key] = value
    return context


def _find_all(node, target_type):
    results = []
    if node.type == target_type:
        results.append(node)
    for child in node.children:
        results.extend(_find_all(child, target_type))
    return results
