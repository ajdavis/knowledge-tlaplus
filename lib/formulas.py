"""Epistemic formula parser: parse formula strings into an AST."""
import re
from dataclasses import dataclass
from pathlib import Path

from lark import Lark, Transformer, v_args

GRAMMAR = r"""
    ?top: or_expr _LEADSTO or_expr -> leads_to
        | or_expr

    ?expr: or_expr

    ?or_expr: and_expr (_OR and_expr)*
    ?and_expr: not_expr (_AND not_expr)*
    ?not_expr: _NOT not_expr -> not_
             | _BOX not_expr -> always
             | _DIAMOND not_expr -> eventually
             | atom

    ?atom: "K" "(" AGENT "," expr ")" -> k
         | "E" "(" expr ")"           -> e
         | "C" "(" expr ")"           -> c
         | "D" "(" expr ")"           -> d
         | "TRUE"                     -> true_
         | "FALSE"                    -> false_
         | NAME "[" INT "]"           -> indexed_var
         | NAME                       -> var
         | "(" expr ")"

    AGENT: INT
    NAME: /[a-zA-Z_]\w*/

    _OR: "\u2228" | "\\/"
    _AND: "\u2227" | "/\\"
    _NOT: "\u00ac" | "~"
    _BOX: "[]"
    _DIAMOND: "<>"
    _LEADSTO: "~>"

    %import common.INT
    %import common.WS
    %ignore WS
"""

parser = Lark(GRAMMAR, start="top", parser="earley")


# AST nodes

@dataclass(frozen=True)
class K:
    agent: int
    body: object
    def __str__(self):
        return f"K({self.agent}, {self.body})"

@dataclass(frozen=True)
class E:
    body: object
    def __str__(self):
        return f"E({self.body})"

@dataclass(frozen=True)
class C:
    body: object
    def __str__(self):
        return f"C({self.body})"

@dataclass(frozen=True)
class D:
    body: object
    def __str__(self):
        return f"D({self.body})"

@dataclass(frozen=True)
class Always:
    body: object
    def __str__(self):
        return f"[]{self.body}"

@dataclass(frozen=True)
class Eventually:
    body: object
    def __str__(self):
        return f"<>{self.body}"

@dataclass(frozen=True)
class LeadsTo:
    left: object
    right: object
    def __str__(self):
        return f"{self.left} ~> {self.right}"

@dataclass(frozen=True)
class Var:
    name: str
    index: int | None = None
    def __str__(self):
        return f"{self.name}[{self.index}]" if self.index is not None else self.name

@dataclass(frozen=True)
class Or:
    left: object
    right: object
    def __str__(self):
        return f"({self.left} \\/ {self.right})"

@dataclass(frozen=True)
class And:
    left: object
    right: object
    def __str__(self):
        return f"({self.left} /\\ {self.right})"

@dataclass(frozen=True)
class Not:
    body: object
    def __str__(self):
        return f"~{self.body}"

@dataclass(frozen=True)
class BoolLit:
    value: bool
    def __str__(self):
        return "TRUE" if self.value else "FALSE"


# Tree transformer

@v_args(inline=True)
class _ASTTransformer(Transformer):
    def k(self, agent, body):
        return K(int(agent), body)

    def e(self, body):
        return E(body)

    def c(self, body):
        return C(body)

    def d(self, body):
        return D(body)

    def always(self, body):
        return Always(body)

    def eventually(self, body):
        return Eventually(body)

    def leads_to(self, left, right):
        return LeadsTo(left, right)

    def var(self, name):
        return Var(str(name))

    def indexed_var(self, name, index):
        return Var(str(name), int(index))

    def true_(self):
        return BoolLit(True)

    def false_(self):
        return BoolLit(False)

    def not_(self, body):
        return Not(body)

    def or_expr(self, *args):
        result = args[0]
        for arg in args[1:]:
            result = Or(result, arg)
        return result

    def and_expr(self, *args):
        result = args[0]
        for arg in args[1:]:
            result = And(result, arg)
        return result


_transformer = _ASTTransformer()


def _needs_parens(node):
    return isinstance(node, (Or, And))


def to_html(ast, _agent=None):
    """Convert AST to Graphviz HTML-label string with subscripts and symbols."""
    match ast:
        case K(agent, body):
            b = to_html(body, _agent=agent)
            if _needs_parens(body):
                b = f"({b})"
            return f"K<SUB>{agent}</SUB> {b}"
        case E(body):
            b = to_html(body, _agent=_agent)
            if _needs_parens(body):
                b = f"({b})"
            return f"E {b}"
        case C(body):
            b = to_html(body, _agent=_agent)
            if _needs_parens(body):
                b = f"({b})"
            return f"C {b}"
        case D(body):
            b = to_html(body, _agent=_agent)
            if _needs_parens(body):
                b = f"({b})"
            return f"D {b}"
        case Var(name, index):
            if index is None or index == _agent:
                return name
            return f"{name}<SUB>{index}</SUB>"
        case Or(left, right):
            return f"{to_html(left, _agent)} &#8744; {to_html(right, _agent)}"
        case And(left, right):
            l = to_html(left, _agent)
            if isinstance(left, Or):
                l = f"({l})"
            r = to_html(right, _agent)
            if isinstance(right, Or):
                r = f"({r})"
            return f"{l} &#8743; {r}"
        case Always(body):
            return f"&#9633; {to_html(body, _agent)}"
        case Eventually(body):
            return f"&#9671; {to_html(body, _agent)}"
        case Not(body):
            return f"&#172;{to_html(body, _agent)}"
        case BoolLit(value):
            return "TRUE" if value else "FALSE"
        case _:
            raise ValueError(f"Unsupported AST node: {ast}")


def parse(text: str):
    """Parse an epistemic formula string into an AST."""
    tree = parser.parse(text)
    return _transformer.transform(tree)


@dataclass
class Property:
    formula: str
    alias: str | None = None


def _extract_annotations(tla_path: str | Path, prefix: str) -> list[Property]:
    props = []
    for line in Path(tla_path).read_text().splitlines():
        line = line.strip()
        if not line.startswith(prefix):
            continue
        text = line.removeprefix(prefix)
        m = re.match(r"([a-zA-Z_]\w*)\s*:\s*", text)
        if m:
            props.append(Property(formula=text[m.end():], alias=m.group(1)))
        else:
            props.append(Property(formula=text))
    return props


def extract_queries(tla_path: str | Path) -> list[Property]:
    r"""Extract ``\* KNOWLEDGE_QUERY`` annotations (per-state evaluation).

    Supports optional alias: ``\* KNOWLEDGE_QUERY psi: K(0, ...)``
    """
    return _extract_annotations(tla_path, r"\* KNOWLEDGE_QUERY ")


def extract_properties(tla_path: str | Path) -> list[Property]:
    r"""Extract ``\* KNOWLEDGE_PROPERTY`` annotations (temporal assertions).

    Must use a temporal operator: ``\* KNOWLEDGE_PROPERTY <>K(0, v[0])``
    """
    return _extract_annotations(tla_path, r"\* KNOWLEDGE_PROPERTY ")


def extract_preconditions(tla_path: str | Path) -> list[Property]:
    r"""Extract ``\* KNOWLEDGE_PRECONDITION`` annotations (label-based assertions).

    Format: ``\* KNOWLEDGE_PRECONDITION label: K(i, φ)`` — asserts the knowledge
    condition holds at all states where ``pc[i] = label``.
    """
    return _extract_annotations(tla_path, r"\* KNOWLEDGE_PRECONDITION ")


def extract_node_label(tla_path: str | Path) -> str | None:
    """Extract NODE_LABEL template from TLA+ file comments."""
    for line in Path(tla_path).read_text().splitlines():
        line = line.strip()
        if line.startswith(r"\* NODE_LABEL "):
            return line.removeprefix(r"\* NODE_LABEL ")
    return None
