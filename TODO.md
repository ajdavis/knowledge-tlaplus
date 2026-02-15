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

## Next
- [ ] Better graph visualization
  - Per-agent colored edges (agent 0=red, 1=blue, 2=darkgreen)
  - Legend subgraph showing agent-to-color mapping
  - Satisfying states highlighted with formula symbol
  - Layout engine selection (sfdp vs neato)
  - These should eventually be configurable via TLA+ annotations
- [ ] Annotate DOT output with property values
