# TODO

## Phase 1: AGENT_STATE expression evaluation

Goal: Move `local_state` from Python to TLA+ in `.knowledge` file.

### 1.1 Setup
- [X] Make a parser

### 1.2 Maybe TLA+ Expression Evaluator? (only if really needed) - on pause
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

## Phase 2: Epistemic operators (K, E, C)

### 2.1 Syntax
```
K(1, muddy[1])          # agent 1 knows muddy[1]
K(1, K(2, muddy[1]))    # nested knowledge
E(m)                    # everyone knows m
C(m)                    # common knowledge of m
```

### 2.2 Evaluation
- [ ] `lib/kripke.py` - evaluate K, E, C on indistinguishability graph
- [ ] Annotate DOT output with property values

## Phase 3: Polish
- [ ] Better graph visualization
