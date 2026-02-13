"""Tests for the epistemic formula parser."""
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from lark.exceptions import UnexpectedInput

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.formulas import (
    And, BoolLit, C, E, K, Not, Or, Var, parse,
)

# -- Atoms --

def test_bare_var():
    assert parse("x") == Var("x")

def test_indexed_var():
    assert parse("r[1]") == Var("r", 1)

def test_true():
    assert parse("TRUE") == BoolLit(True)

def test_false():
    assert parse("FALSE") == BoolLit(False)

# -- Knowledge operators --

def test_k_basic():
    assert parse("K(0, x)") == K(0, Var("x"))

def test_k_nested():
    assert parse("K(0, K(1, x))") == K(0, K(1, Var("x")))

def test_e():
    assert parse("E(x)") == E(Var("x"))

def test_c():
    assert parse("C(x)") == C(Var("x"))

# -- Boolean operators (ASCII and Unicode) --

def test_or_ascii():
    assert parse(r"x \/ y") == Or(Var("x"), Var("y"))

def test_or_unicode():
    assert parse("x \u2228 y") == Or(Var("x"), Var("y"))

def test_and_ascii():
    assert parse(r"x /\ y") == And(Var("x"), Var("y"))

def test_and_unicode():
    assert parse("x \u2227 y") == And(Var("x"), Var("y"))

def test_not_ascii():
    assert parse("~x") == Not(Var("x"))

def test_not_unicode():
    assert parse("\u00acx") == Not(Var("x"))

# -- Precedence and associativity --

def test_not_binds_tighter_than_and():
    assert parse(r"~x /\ y") == And(Not(Var("x")), Var("y"))

def test_and_binds_tighter_than_or():
    assert parse(r"x \/ y /\ z") == Or(Var("x"), And(Var("y"), Var("z")))

def test_or_left_associative():
    assert parse(r"x \/ y \/ z") == Or(Or(Var("x"), Var("y")), Var("z"))

def test_and_left_associative():
    assert parse(r"x /\ y /\ z") == And(And(Var("x"), Var("y")), Var("z"))

def test_parens_override_precedence():
    assert parse(r"(x \/ y) /\ z") == And(Or(Var("x"), Var("y")), Var("z"))

# -- Complex expression --

def test_raft_formula():
    result = parse(r"K(0, K(1, r[1]) \/ K(2, r[2]))")
    expected = K(0, Or(K(1, Var("r", 1)), K(2, Var("r", 2))))
    assert result == expected

# -- __str__ roundtrips --

@pytest.mark.parametrize("text,expected_str", [
    ("x", "x"),
    ("r[1]", "r[1]"),
    ("TRUE", "TRUE"),
    ("FALSE", "FALSE"),
    ("K(0, x)", "K(0, x)"),
    ("E(x)", "E(x)"),
    ("C(x)", "C(x)"),
    ("~x", "~x"),
    (r"x \/ y", r"(x \/ y)"),
    (r"x /\ y", r"(x /\ y)"),
])
def test_str_representation(text, expected_str):
    assert str(parse(text)) == expected_str

def test_str_roundtrip_complex():
    expr = parse(r"K(0, K(1, r[1]) \/ K(2, r[2]))")
    assert parse(str(expr)) == expr

# -- Syntax errors --

def test_missing_paren():
    with pytest.raises(UnexpectedInput):
        parse("K(0, x")

def test_missing_agent():
    with pytest.raises(UnexpectedInput):
        parse("K(x)")

def test_empty_string():
    with pytest.raises(UnexpectedInput):
        parse("")

# -- Property-based tests --

ast_strategy = st.recursive(
    st.one_of(
        st.from_regex(r"[a-z]{1,4}", fullmatch=True).map(lambda n: Var(n)),
        st.tuples(
            st.from_regex(r"[a-z]{1,4}", fullmatch=True),
            st.integers(0, 99),
        ).map(lambda t: Var(t[0], t[1])),
        st.just(BoolLit(True)),
        st.just(BoolLit(False)),
    ),
    lambda children: st.one_of(
        st.tuples(st.integers(0, 9), children).map(lambda t: K(t[0], t[1])),
        children.map(E),
        children.map(C),
        children.map(Not),
        st.tuples(children, children).map(lambda t: Or(t[0], t[1])),
        st.tuples(children, children).map(lambda t: And(t[0], t[1])),
    ),
    max_leaves=10,
)

@given(expr=ast_strategy)
@settings(max_examples=200)
def test_roundtrip_property(expr):
    assert parse(str(expr)) == expr
