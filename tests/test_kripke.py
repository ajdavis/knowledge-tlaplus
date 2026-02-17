"""Test epistemic formula evaluation against a TLC state graph."""
import subprocess
import sys
from pathlib import Path

import pytest
from networkx.drawing.nx_pydot import write_dot

sys.path.insert(0, str(Path(__file__).parent.parent))
from analyze import _states_at_label, _check_precondition
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

    return node_map, eq_classes, names, G


def _eval(expr_str, model):
    return kripke.eval_formula(formulas.parse(expr_str), model[0], model[1])


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


# -- D (distributed knowledge) --

def test_d_conjunction(model):
    r"""D(v[0] /\ v[1]) holds at both — the intersection of equiv classes is
    {both}, and v[0]/\v[1] holds there. E(v[0] /\ v[1]) holds nowhere."""
    assert _eval(r"D(v[0] /\ v[1])", model) == _states(model, "both")
    assert _eval(r"E(v[0] /\ v[1])", model) == set()

def test_d_superset_of_e(model):
    """D(φ) ⊇ E(φ) for several formulas."""
    for formula in ["v[0]", "v[1]", r"v[0] \/ v[1]", r"v[0] /\ v[1]", "w[0]"]:
        d_states = _eval(f"D({formula})", model)
        e_states = _eval(f"E({formula})", model)
        assert d_states >= e_states, f"D ⊉ E for {formula}"

def test_d_private_var(model):
    """D(v[0]) holds wherever v[0] is true — intersections are all singletons
    in KripkeTest, so D reduces to the formula itself."""
    assert _eval("D(v[0])", model) == _states(model, "act0", "both")


# -- Temporal properties --
# KripkeTest state graph: init → act0 → both, init → act1 → both

def test_always_pass(model):
    r"""Agent 0 always knows w[0]'s value (true or false)."""
    sat = _eval(r"K(0, w[0]) \/ K(0, ~w[0])", model)
    assert sat == _states(model, "init", "act0", "act1", "both")
    passed, violations = kripke.check_always(sat, set(model[0].keys()))
    assert passed
    assert violations == set()

def test_always_fail(model):
    """[]K(0, v[0]) fails at init and act1."""
    sat = _eval("K(0, v[0])", model)
    passed, violations = kripke.check_always(sat, set(model[0].keys()))
    assert not passed
    assert violations == _states(model, "init", "act1")

def test_eventually_pass(model):
    """<>K(0, v[0]) — every path reaches a state where agent 0 knows v[0]."""
    sat = _eval("K(0, v[0])", model)
    passed, violations = kripke.check_eventually(model[3], sat)
    assert passed

def test_eventually_fail(model):
    """<>K(0, v[1]) — fails: path init→act0→both never reaches K(0, v[1])."""
    sat = _eval("K(0, v[1])", model)
    passed, violations = kripke.check_eventually(model[3], sat)
    assert not passed

def test_leads_to_pass(model):
    """w[0] ~> K(0, v[0]) — whenever w[0] holds, K(0, v[0]) eventually follows."""
    psi = _eval("w[0]", model)
    phi = _eval("K(0, v[0])", model)
    passed, violations = kripke.check_leads_to(model[3], psi, phi)
    assert passed

def test_leads_to_fail(model):
    """v[1] ~> K(0, v[1]) — fails at both (terminal, K(0, v[1]) doesn't hold)."""
    psi = _eval("v[1]", model)
    phi = _eval("K(0, v[1])", model)
    passed, violations = kripke.check_leads_to(model[3], psi, phi)
    assert not passed
    assert _states(model, "both").issubset(violations)


# -- _states_at_label --

def test_states_at_label():
    """Unit test: find states by pc label in a small state graph."""
    node_map = {
        "fp1": {"pc": {"0": "SendFirst", "1": "ReceiveAndAck", "2": "ReceiveAndAck"}},
        "fp2": {"pc": {"0": "ReceiveAck1", "1": "Done", "2": "ReceiveAndAck"}},
        "fp3": {"pc": {"0": "AcknowledgeCommand", "1": "Done", "2": "Done"}},
    }
    collapse_map = {"fp1": "fp1", "fp2": "fp2", "fp3": "fp3"}
    assert _states_at_label("AcknowledgeCommand", node_map, collapse_map) == {"fp3"}
    assert _states_at_label("ReceiveAndAck", node_map, collapse_map) == {"fp1", "fp2"}
    assert _states_at_label("Nonexistent", node_map, collapse_map) == set()


def test_states_at_label_with_collapse():
    """States with the same label collapse to the same representative."""
    node_map = {
        "fp1": {"pc": {"0": "Label"}},
        "fp2": {"pc": {"0": "Label"}},
    }
    collapse_map = {"fp1": "fp1", "fp2": "fp1"}  # fp2 collapses to fp1
    assert _states_at_label("Label", node_map, collapse_map) == {"fp1"}


# -- Precondition integration test --

RAFT_DIR = Path(__file__).parent.parent / "raft"


@pytest.fixture(scope="module")
def raft_model():
    """Run TLC on SimpleRaft and return components for precondition checking."""
    from analyze import collapse_states

    tla_path = RAFT_DIR / "SimpleRaft.tla"
    tlc.run(tla_path)
    G, node_map, _ = tlc.parse_state_graph(RAFT_DIR / "SimpleRaft")
    processes = pcal.parse_processes(tla_path)
    agents = pcal.get_agents(node_map)
    agent_map = pcal.map_agents_to_processes(processes, node_map)

    def local_state_fn(state, agent):
        return pcal.get_local_state(state, agent, agent_map)

    kripke.validate_state_transitions(G, node_map, agents, local_state_fn)
    states, collapse_map = collapse_states(node_map, agents, local_state_fn)
    eq_classes = kripke.build_equivalence_classes(states, agents, local_state_fn)
    return node_map, collapse_map, states, eq_classes


def test_raft_precondition_pass(raft_model):
    """AcknowledgeCommand precondition passes: leader knows a follower knows."""
    node_map, collapse_map, states, eq_classes = raft_model
    ast = formulas.parse(r"K(0, K(1, received[1]) \/ K(2, received[2]))")
    label_kwargs = dict(template=None, processes=None, agent_map=None)
    assert _check_precondition("AcknowledgeCommand", ast, node_map, collapse_map,
                               states, eq_classes, label_kwargs)
