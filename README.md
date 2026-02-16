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

## Usage

Annotate a `.tla` file with epistemic properties and node label formatting:

```tla
\* NODE_LABEL acks: {acks}\nreceived: {received}\nsent: {sent}
\* KNOWLEDGE_PROPERTY psi: K(0, K(1, received[1]) \/ K(2, received[2]))
```

Run the generic analysis tool:

```bash
.venv/bin/python3 analyze.py raft/SimpleRaft.tla
```

This runs TLC, builds the Kripke structure, evaluates each property, and generates a DOT/PDF
indistinguishability graph with custom node labels and satisfying states highlighted.

## Architecture

1. **TLA+/PlusCal spec** — each PlusCal process is an agent; process-local variables define what
   the agent can observe. Global variables (e.g. a network) are used for communication but are not
   part of any agent's local state.
2. **`analyze.py`** — generic analysis tool. Extracts `KNOWLEDGE_PROPERTY` annotations from the
   `.tla` file, runs TLC, builds the Kripke structure, evaluates formulas, and generates
   visualizations.
3. **`lib/pcal.py`** parses PlusCal to extract the process-to-variable mapping, then maps TLC
   agent IDs to processes via initial `pc` labels.
4. **`lib/kripke.py`** builds indistinguishability equivalence classes and the Kripke structure
   from the agent observation model.
5. **`lib/formulas.py`** parses epistemic formulas (K, E, C, D, boolean connectives) and temporal
   operators ([], <>, ~>), and evaluates them on the Kripke structure.
6. **`lib/tlc.py`** runs TLC and parses the JSON state graph output.

## Epistemic Semantics

- **K(i, φ)** at state s: φ holds at all states indistinguishable from s for agent i
- **E(φ)**: K(i, φ) for all agents i (everyone knows)
- **D(φ)**: φ holds at all states in the intersection of all agents' equivalence classes
  (distributed knowledge — what the group would know if they pooled their information)
- **C(φ)**: fixed point — φ holds at all states reachable via indistinguishability edges
  (common knowledge)

### Temporal Operators

Temporal operators can be used in `KNOWLEDGE_PROPERTY` annotations to check properties across the
whole state graph (not just individual states):

- **[]φ**: invariant — φ holds at every reachable state
- **<>φ**: liveness — on every execution path, φ eventually holds
- **ψ ~> φ**: leads-to — whenever ψ holds, φ eventually follows on all paths

```tla
\* KNOWLEDGE_PROPERTY [](K(0, w[0]) \/ K(0, ~w[0]))
\* KNOWLEDGE_PROPERTY <>K(0, v[0])
\* KNOWLEDGE_PROPERTY sent[1] ~> K(1, received[1])
```

Two states are indistinguishable for agent i when the agent's process-local variables have the
same values in both states. See [docs/writing-specs.md](docs/writing-specs.md) for details on
writing specs for knowledge analysis.
