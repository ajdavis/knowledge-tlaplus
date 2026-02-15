# TODO

## Done
- [X] Epistemic formula parser (`lib/formulas.py`)
- [X] Kripke structure evaluation: K, E, C (`lib/kripke.py`)
- [X] PlusCal process-local variable parsing (`lib/pcal.py`)
- [X] Automatic agent-to-process mapping via `pc` labels
- [X] SimpleRaft analysis with message-passing network
- [X] One script that can do epistemic analysis on any PlusCal spec, given epistemic properties
      in a comment (`analyze.py` + `KNOWLEDGE_PROPERTY` annotations in `.tla` files)
- [X] CardGame uses process-local `hand` variable
- [N/A] MuddyChildren: PlusCal can't model simultaneous transitions, stays as controller pattern

- [X] Graph visualization: per-agent colored edges, legend, satisfying states highlighted,
      compact neato layout with scalexy + position scaling
- [X] `NODE_LABEL` annotation for custom node label formatting (Python f-string template)
- [X] `KNOWLEDGE_PROPERTY` alias support (e.g., `psi: K(0, ...)`) displayed on satisfying nodes
- [X] Set-process local vars displayed as agent-keyed dicts in node labels

## Next
