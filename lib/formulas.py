"""Epistemic formula parser: parse formula strings into an AST."""
import re
from dataclasses import dataclass
from pathlib import Path

from lark import Lark, Transformer, v_args

GRAMMAR = r"""
    ?expr: or_expr

    ?or_expr: and_expr (_OR and_expr)*
    ?and_expr: not_expr (_AND not_expr)*
    ?not_expr: _NOT not_expr -> not_
             | atom

    ?atom: "K" "(" AGENT "," expr ")" -> k
         | "E" "(" expr ")"           -> e
         | "C" "(" expr ")"           -> c
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

    %import common.INT
    %import common.WS
    %ignore WS
"""

parser = Lark(GRAMMAR, start="expr", parser="earley")


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


def parse(text: str):
    """Parse an epistemic formula string into an AST."""
    tree = parser.parse(text)
    return _transformer.transform(tree)


@dataclass
class Property:
    formula: str
    alias: str | None = None


def extract_properties(tla_path: str | Path) -> list[Property]:
    """Extract KNOWLEDGE_PROPERTY annotations from TLA+ file comments.

    Supports optional alias: ``\\* KNOWLEDGE_PROPERTY psi: K(0, ...)``
    """
    props = []
    for line in Path(tla_path).read_text().splitlines():
        line = line.strip()
        if not line.startswith(r"\* KNOWLEDGE_PROPERTY "):
            continue
        text = line.removeprefix(r"\* KNOWLEDGE_PROPERTY ")
        m = re.match(r"([a-zA-Z_]\w*)\s*:\s*", text)
        if m:
            props.append(Property(formula=text[m.end():], alias=m.group(1)))
        else:
            props.append(Property(formula=text))
    return props


def extract_node_label(tla_path: str | Path) -> str | None:
    """Extract NODE_LABEL template from TLA+ file comments."""
    for line in Path(tla_path).read_text().splitlines():
        line = line.strip()
        if line.startswith(r"\* NODE_LABEL "):
            return line.removeprefix(r"\* NODE_LABEL ")
    return None
