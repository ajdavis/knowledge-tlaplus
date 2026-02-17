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

- [X] Distributed knowledge operator D
  - D_G(φ) holds at state s iff φ holds at all states in the *intersection* of all agents'
    equivalence classes containing s. It represents what the group would know if they pooled
    their information. See Halpern & Moses Section 3 (p.5) definition and Section 6 (p.13-14)
    formal semantics: D_G holds at (r,t) iff φ holds at all (r',t') where v(p_i,r,t) =
    v(p_i,r',t') for ALL p_i in G.
  - Implementation: add `eval_d(phi_states, eq_classes)` to `lib/kripke.py`. For each state s,
    compute the intersection of s's equivalence classes across all agents. If φ holds at all
    states in that intersection, D(φ) holds at s. Add `D` AST node and parser rule to
    `lib/formulas.py` (syntax: `D(φ)`), and handle it in `eval_formula`.
  - The knowledge hierarchy should be testable: D(φ) ⊃ S(φ) ⊃ E(φ) ⊃ C(φ). (S = "someone
    knows" = ∨ K_i; we don't need to implement S, just verify D ⊇ E in tests.)
  - Test in `tests/test_kripke.py` using the existing KripkeTest.tla spec. KripkeTest has
    2 agents with variables v (private) and w (public announcement). The intersection of
    agent 0's and agent 1's equiv classes should be finer than either alone. Example:
    `D(v[0] /\ v[1])` should hold at `both` (where the intersection of equiv classes is just
    {both}), while `E(v[0] /\ v[1])` holds nowhere (each agent has an equiv class containing
    a state where the other's v is false). This demonstrates the gap between distributed and
    individual knowledge. Also test that D(φ) ⊇ E(φ) for several formulas.

- [X] Temporal epistemic properties — check knowledge properties across the whole spec
  - Currently we evaluate `K(i, φ)` at individual states. TLA+ checks safety and liveness
    properties across all behaviors of a spec. Combine these ideas to check epistemic temporal
    properties on the TLC state graph.
  - Use the existing `KNOWLEDGE_PROPERTY` annotation with temporal operators in the formula
    language. The temporal operator at the top of the AST determines the check type:
    - `[]φ` → invariant check
    - `<>φ` → liveness check
    - `ψ ~> φ` → leads-to check
    - bare `φ` → evaluate at individual states (current behavior)
  - Add `Always`, `Eventually`, `LeadsTo` AST nodes and parser rules to `lib/formulas.py`.
    Handle them in `analyze.py` (not `eval_formula`, since they operate on the state graph
    rather than individual states).

  - [X] Invariant: `[]K(i, φ)` — knowledge property holds at every reachable state
    - Check whether sat_states == all states. Report pass/fail with counterexample states.
    - Annotation: `\* KNOWLEDGE_PROPERTY [](K(0, w[0]) \/ K(0, ~w[0]))`
    - Test in `tests/test_kripke.py` using KripkeTest.tla:
      `[](K(0, w[0]) \/ K(0, ~w[0]))` — agent 0 always knows w[0]'s value — should pass
      (holds at all 4 states). `[]K(0, v[0])` should fail (fails at `init` and `act1`).

  - [X] Liveness: `<>K(i, φ)` — on every execution path, the property eventually holds
    - Check that every maximal path through the TLC state graph eventually reaches a state
      satisfying the knowledge formula. Equivalently: no cycle in the state graph avoids all
      satisfying states, and no path from an initial state reaches a dead end without passing
      through a satisfying state.
    - Implementation: using the TLC state graph (a directed graph from `tlc.parse_state_graph`),
      compute the set of states from which a satisfying state is unreachable. If any initial
      state is in this set, liveness fails. Use SCC analysis: if any SCC in the graph contains
      no satisfying state and has no outgoing edge to a satisfying state, liveness fails for
      states in that SCC.
    - Annotation: `\* KNOWLEDGE_PROPERTY <>K(0, v[0])`
    - Test: in KripkeTest.tla (or a new spec), `<>K(0, v[0])` should pass because agent 0
      eventually acts and learns v[0]=T.

  - [X] Leads-to: `ψ ~> K(i, φ)` — whenever ψ holds, K(i, φ) eventually follows
    - Standard TLA+ leads-to: for every state satisfying ψ, every maximal path from that state
      eventually reaches a state satisfying K(i, φ).
    - Annotation: `\* KNOWLEDGE_PROPERTY w[0] ~> K(0, v[0])`
    - This captures "communication causes knowledge gain": e.g., in SimpleRaft, after a follower
      sends an ack (ψ), the leader eventually knows the follower received (K(0, received[f])).

- [ ] Knowledge evolution along traces
  - Rather than showing which states satisfy a formula, visualize how knowledge evolves along
    execution traces through the TLC state graph.
  - For each path from an initial state to a terminal state, annotate states with the knowledge
    properties that first become true at that step. This makes concrete the paper's idea (p.7)
    that "communication is the act of climbing up the knowledge hierarchy."
  - Implementation: enumerate representative traces (paths) through the directed TLC state
    graph. For each trace, evaluate all declared knowledge properties at each state and report
    which properties are newly satisfied. Could generate a timeline visualization (annotated
    DOT graph of the trace, or text output).
  - In SimpleRaft, this would show: (1) initial state — no knowledge, (2) after SendFirst —
    leader knows sent[f]=T, (3) after ReceiveAndAck — follower knows received[f]=T,
    (4) after ReceiveAck — leader knows the follower received. The knowledge hierarchy
    visibly climbs with each communication step.

- [X] Coordinated attack spec
  - PlusCal spec for the coordinated attack problem (Halpern & Moses Section 4, p.8).
    Two generals, 3 rounds of unreliable communication. Demonstrates knowledge hierarchy
    climbing (K, KK, KKK) while common knowledge C never holds.
  - `coordinated-attack/CoordinatedAttack.tla`
  
- [ ] Improve aliases:
  - allow richer identifiers with spaces and parens etc
  - perhaps LaTeX?
  - or format the knowledge expr itself and get rid of aliases?

- [ ] Knowledge-based protocol verification
  - The paper (Section 14, p.36) mentions "knowledge-based protocols" where a processor's
    actions are explicitly conditioned on its knowledge. Implement a way to annotate PlusCal
    actions with knowledge preconditions and verify that the protocol satisfies them.
  - New annotation: `KNOWLEDGE_PRECONDITION label: K(i, φ)` — asserts that whenever the
    PlusCal label `label` is enabled (i.e., the state has `pc[i] = label`), the knowledge
    condition `K(i, φ)` holds. This checks that the protocol only takes an action when the
    agent actually has the knowledge the protocol designer intended.
  - Example in SimpleRaft: annotate `ReceiveAck1` with a precondition that the leader knows
    at least one follower has received (the ack message in the network witnesses this).
  - Implementation: for each precondition annotation, find all states where the label is
    enabled (pc matches), evaluate the knowledge formula, and check containment. Report
    violations as states where the action fires without the required knowledge.

- [ ] Revisit Muddy Children with Halpern & Moses results
  - The muddy children puzzle is analyzed extensively in Halpern & Moses (Section 2, p.3-4
    and Section 3, p.6). Key results: (1) before the father speaks, E^(k-1)(m) holds but not
    E^k(m) when there are k muddy children, (2) the father's announcement makes m common
    knowledge, (3) E^k(m) is sufficient for the muddy children to identify themselves after k
    rounds.
  - Using our MuddyChildren spec and analysis tools, try to derive these results
    semi-mechanically: (a) verify that C(m) holds after the father's announcement (round 0
    states), (b) check E^k(m) at each round and confirm it increases, (c) verify that the
    muddy children's "saidYes" action correlates with attaining sufficient E^k knowledge.
  - This may require adding E^k (iterated everyone-knows) to the formula language:
    `E^k(φ) = E(E(...E(φ)...))` k times. Could be syntactic sugar in the parser.
  - The MuddyChildren spec uses the controller pattern (not PlusCal per-agent processes) so
    it uses its own analysis script, not `analyze.py`. The E^k analysis might need to be
    added to that script or generalized.
