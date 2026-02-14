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

1. **TLA+/PlusCal spec** — each PlusCal process is an agent; process-local variables define what
   the agent can observe. Global variables (e.g. a network) are used for communication but are not
   part of any agent's local state.
2. **`lib/pcal.py`** parses PlusCal to extract the process-to-variable mapping, then maps TLC
   agent IDs to processes via initial `pc` labels.
3. **`lib/kripke.py`** builds indistinguishability equivalence classes and the Kripke structure
   from the agent observation model.
4. **`lib/formulas.py`** parses epistemic formulas (K, E, C, boolean connectives) and evaluates
   them on the Kripke structure.
5. **`lib/tlc.py`** runs TLC and parses the JSON state graph output.

## Epistemic Semantics

- **K(i, φ)** at state s: φ holds at all states indistinguishable from s for agent i
- **E(φ)**: K(i, φ) for all agents i (everyone knows)
- **C(φ)**: fixed point — φ holds at all states reachable via indistinguishability edges
  (common knowledge)

Two states are indistinguishable for agent i when the agent's process-local variables have the
same values in both states. See [docs/writing-specs.md](docs/writing-specs.md) for details on
writing specs for knowledge analysis.
