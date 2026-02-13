# Knowledge + TLA+

Exploring epistemic logic (reasoning about knowledge) combined with TLA+ temporal logic.

Based on Halpern & Moses, "Knowledge and Common Knowledge in a Distributed Environment" (1990).

## Setup

Requires: Java 11, Ant, Graphviz, Python 3.

```bash
brew install openjdk@11 ant graphviz
./build-tlc.sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Tests

```bash
.venv/bin/pytest tests/
```

A pre-commit hook runs tests and all analysis scripts. Enable it with:

```bash
git config core.hooksPath .githooks
```

## Architecture

1. **TLA+/PlusCal spec** → TLC → state graph (JSON)
2. **`.knowledge` file** declares AGENT_STATE (what each agent sees) and epistemic properties
3. **`lib/tla_eval.py`** evaluates TLA+ expressions against state values (uses tree-sitter-tlaplus)
4. **`lib/knowledge.py`** builds indistinguishability graph (Kripke structure) using AGENT_STATE
5. **`lib/epistemic.py`** evaluates K, E, C properties on the graph

## .knowledge File Format

```
# AGENT_STATE: TLA+ expression defining what agent `self` can observe
# Used to determine state indistinguishability (like TLA+ VIEW)
AGENT_STATE(self) == <<
  {j \in Children : j /= self /\ muddy[j]},
  {j \in Children : saidYes[j]},
  m,
  q
>>

# Epistemic properties to evaluate
K(1, muddy[1])          # agent 1 knows muddy[1]
K(1, K(2, muddy[1]))    # agent 1 knows that agent 2 knows muddy[1]
E(m)                    # everyone knows m
C(m)                    # common knowledge of m
```

## Epistemic Semantics (Kripke/view-based)

- **K(i, φ)** at state s: φ holds at s and all s' where AGENT_STATE(i) is equal
- **E(φ)**: K(i, φ) for all agents i
- **C(φ)**: φ holds at all states reachable via indistinguishability edges
