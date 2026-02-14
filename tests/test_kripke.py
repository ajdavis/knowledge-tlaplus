"""Test epistemic formula evaluation against a TLC state graph."""
import subprocess
import sys
from pathlib import Path

import pytest
from networkx.drawing.nx_pydot import write_dot

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib import tlc, kripke, formulas, pcal

THIS_DIR = Path(__file__).parent


def _local_state(state, agent):
    """Agent i observes (v[i], w[i])."""
    return (kripke._lookup(state["v"], int(agent)),
            kripke._lookup(state["w"], int(agent)))


@pytest.fixture(scope="module")
def model():
    """Run TLC on KripkeTest and return (node_map, eq_classes, state_index).

    KripkeTest has 2 agents {0,1}, variables v (private bool) and w (public
    announcement). 4 states:
      init:  v=(F,F), w=(F,F)  — nothing happened
      act0:  v=(T,F), w=(T,T)  — agent 0 acted
      act1:  v=(F,T), w=(T,T)  — agent 1 acted
      both:  v=(T,T), w=(T,T)  — both acted

    Agent 0 sees (v[0], w[0]), Agent 1 sees (v[1], w[1]).

    Equivalence classes:
      Agent 0: {init}, {act0, both}, {act1}
      Agent 1: {init}, {act0}, {act1, both}

    Indistinguishability graph has two components:
      {init} and {act0, act1, both}
    """
    tlc.run(THIS_DIR / "KripkeTest.tla")
    G, node_map, _ = tlc.parse_state_graph(THIS_DIR / "KripkeTest")
    agents = pcal.get_agents(node_map)
    kripke.validate_state_transitions(G, node_map, agents, _local_state)
    eq_classes = kripke.build_equivalence_classes(node_map, agents, _local_state)

    # Index states by (v[0], v[1]) for readable assertions
    state_index = {}
    for fp, s in node_map.items():
        key = (s["v"]["0"], s["v"]["1"])
        state_index[key] = fp

    init = state_index[(False, False)]
    act0 = state_index[(True, False)]
    act1 = state_index[(False, True)]
    both = state_index[(True, True)]
    names = {"init": init, "act0": act0, "act1": act1, "both": both}
    fp_to_name = {fp: name for name, fp in names.items()}

    # Build indistinguishability graph and write DOT/PDF
    indist_G, agents = kripke.build_indistinguishability_graph(node_map, eq_classes)
    agent_colors = {"0": "red", "1": "blue"}
    for fp in indist_G.nodes():
        s = node_map[fp]
        v0, v1 = s["v"]["0"], s["v"]["1"]
        w0 = s["w"]["0"]
        label = f"{fp_to_name[fp]}\\nv=({int(v0)},{int(v1)}) w={int(w0)}"
        indist_G.nodes[fp]["label"] = label
    for u, v, data in indist_G.edges(data=True):
        agent_list = data["agents"]
        indist_G.edges[u, v]["label"] = ",".join(agent_list)
        if len(agent_list) == 1:
            indist_G.edges[u, v]["color"] = agent_colors[agent_list[0]]
        else:
            indist_G.edges[u, v]["color"] = ":".join(
                agent_colors[a] for a in agent_list
            )
    indist_G.graph["graph"] = {"overlap": "false"}

    dot_path = THIS_DIR / "KripkeTest-indistinguishability.dot"
    write_dot(indist_G, dot_path)
    pdf_path = THIS_DIR / "KripkeTest-indistinguishability.pdf"
    subprocess.check_call(["neato", "-Tpdf", dot_path, "-o", pdf_path])

    return node_map, eq_classes, names


def _eval(expr_str, model):
    node_map, eq_classes, _ = model
    return kripke.eval_formula(formulas.parse(expr_str), node_map, eq_classes)


def _states(model, *names):
    return {model[2][n] for n in names}


# -- Var and BoolLit --

def test_var_indexed(model):
    assert _eval("v[0]", model) == _states(model, "act0", "both")
    assert _eval("v[1]", model) == _states(model, "act1", "both")
    assert _eval("w[0]", model) == _states(model, "act0", "act1", "both")

def test_bool_lit(model):
    assert _eval("TRUE", model) == _states(model, "init", "act0", "act1", "both")
    assert _eval("FALSE", model) == set()


# -- Boolean connectives --

def test_not(model):
    assert _eval("~v[0]", model) == _states(model, "init", "act1")

def test_and(model):
    assert _eval(r"v[0] /\ v[1]", model) == _states(model, "both")

def test_or(model):
    assert _eval(r"v[0] \/ v[1]", model) == _states(model, "act0", "act1", "both")


# -- K (individual knowledge) --

def test_k_own_var(model):
    """Each agent knows its own v value when it's true."""
    assert _eval("K(0, v[0])", model) == _states(model, "act0", "both")
    assert _eval("K(1, v[1])", model) == _states(model, "act1", "both")

def test_k_other_var(model):
    """Agent 0 knows v[1] only at act1 (where agent 0's local state is unique)."""
    assert _eval("K(0, v[1])", model) == _states(model, "act1")
    assert _eval("K(1, v[0])", model) == _states(model, "act0")

def test_k_disjunction(model):
    assert _eval(r"K(0, v[0] \/ v[1])", model) == _states(model, "act0", "act1", "both")

def test_k_nested(model):
    """Agent 0 knows that agent 1 knows v[1]: only at act1."""
    assert _eval("K(0, K(1, v[1]))", model) == _states(model, "act1")


# -- E (everyone knows) --

def test_e(model):
    assert _eval(r"E(v[0] \/ v[1])", model) == _states(model, "act0", "act1", "both")

def test_e_conjunction(model):
    r"""Nobody knows v[0] /\ v[1] because each agent has an equiv class
    containing a state where the other's v is false."""
    assert _eval(r"E(v[0] /\ v[1])", model) == set()


# -- C (common knowledge) --

def test_c_nontrivial(model):
    r"""v[0] \/ v[1] is common knowledge in the {act0, act1, both} component
    but not at init."""
    assert _eval(r"C(v[0] \/ v[1])", model) == _states(model, "act0", "act1", "both")

def test_c_nontrivial_other(model):
    r"""~v[0] /\ ~v[1] is common knowledge only at init (its own component)."""
    assert _eval(r"C(~v[0] /\ ~v[1])", model) == _states(model, "init")

def test_c_true(model):
    assert _eval("C(TRUE)", model) == _states(model, "init", "act0", "act1", "both")

def test_c_private_var(model):
    """v[0] alone is never common knowledge (fails in the 3-state component)."""
    assert _eval("C(v[0])", model) == set()

def test_c_public_var(model):
    """w[0] is common knowledge in the {act0, act1, both} component."""
    assert _eval("C(w[0])", model) == _states(model, "act0", "act1", "both")
