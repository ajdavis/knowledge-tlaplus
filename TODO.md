# TODO

## Phase 1: AGENT_STATE expression evaluation

Goal: Move `local_state` from Python to TLA+ in `.knowledge` file.

### 1.1 Setup
- [ ] Add tree-sitter, tree-sitter-tlaplus to requirements.txt
- [ ] Create `lib/tla_eval.py` - TLA+ expression evaluator

### 1.2 TLA+ Expression Evaluator
Parse with tree-sitter-tlaplus, evaluate against state dict. Support:
- Variables: `muddy`, `m`, `q`, `saidYes`
- Parameters: `self` (agent id)
- Indexing: `muddy[j]`
- Boolean: `/\`, `\/`, `~`, `=>`, `<=>`
- Comparison: `=`, `/=`, `<`, `>`, `<=`, `>=`
- Sets: `{}`, `{a,b}`, `{x \in S : P(x)}`
- Tuples: `<<a, b>>`
- Quantifiers: `\A`, `\E`
- CONSTANT values from .cfg: `Children`, `N`

### 1.3 .knowledge file format
```
# MuddyChildren.knowledge

AGENT_STATE(self) == <<
  {j \in Children : j /= self /\ muddy[j]},
  {j \in Children : saidYes[j]},
  m,
  q
>>
```

### 1.4 Integration
- [ ] Create `lib/knowledge_file.py` - parse .knowledge files
- [ ] Update `lib/kripke.py` to accept AGENT_STATE expression
- [ ] Move generic logic from `muddy-children-knowledge-analysis.py:41-67` into lib/

## Phase 2: Epistemic operators (K, E, C)

### 2.1 Syntax in .knowledge
```
K(1, muddy[1])          # agent 1 knows muddy[1]
K(1, K(2, muddy[1]))    # nested knowledge
E(m)                    # everyone knows m
C(m)                    # common knowledge of m
```

### 2.2 Evaluation
- [ ] `lib/formulas.py` - evaluate K, E, C on indistinguishability graph
- [ ] Annotate DOT output with property values

## Phase 3: Polish
- [ ] Better graph visualization
- [ ] More TLA+ expression coverage as needed

## Notes

tree-sitter-tlaplus: https://github.com/tlaplus-community/tree-sitter-tlaplus
- Requires wrapping expressions in a TLA+ module to parse
- Returns AST, we evaluate it ourselves
