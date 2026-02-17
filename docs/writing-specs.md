# Writing TLA+/PlusCal Specs for Knowledge Analysis

## Agent Observation Model

Each PlusCal process represents an agent. An agent's **local state** — what it can observe — is
defined by its process-local variables. The `pcal.py` module parses the PlusCal source to extract
the mapping from processes to local variables, and uses it to compute each agent's observations
automatically.

For a **set process** (`\in expr`), each agent sees its own index into the variable. For a
**singleton process** (`= expr`), the agent sees the whole variable value.

Example from SimpleRaft:

```pluscal
process LeaderProc = Leader
variables
    sent = [f \in Followers |-> FALSE],
    acks = [f \in Followers |-> FALSE];
begin ...

process FollowerProc \in Followers
variable received = FALSE;
begin ...
```

- Agent 0 (leader, singleton) observes: `(sent, acks)`
- Agent 1 (follower, set) observes: `(received[1],)`
- Agent 2 (follower, set) observes: `(received[2],)`

`analyze.py` derives this automatically from the PlusCal source.

Global variables (like `network`) are not part of any agent's local state. Use them for
communication channels that agents read from and write to, updating their own local variables
to record what they've learned.

## Annotations

Add annotations as TLA+ comments (before `\* BEGIN TRANSLATION`).

### Process-Local Variables

PlusCal translates each set-process local variable into a TLA+ function indexed by process ID.
In annotations, use the TLA+ form — `rcvd[0]`, `rcvd[1]` — not the PlusCal form `rcvd`:

```pluscal
process Gen \in {0, 1}
variables sent = 0, rcvd = 0;
```

```tla
\* KNOWLEDGE_QUERY K(1, rcvd[1])          \* general 1's local rcvd
\* KNOWLEDGE_QUERY K(0, rcvd[1])          \* general 0 knows general 1's rcvd
\* KNOWLEDGE_PROPERTY <>K(0, sent[0])     \* NOT just "sent"
```

Singleton-process local variables are not indexed.

### Knowledge Queries (Exploratory)

Evaluate an epistemic formula at each state and show which states satisfy it:

```tla
\* KNOWLEDGE_QUERY K(0, K(1, received[1]) \/ K(2, received[2]))
```

Satisfying states are highlighted yellow in the PDF. To also display a label on those nodes, add
an alias — without one, no text appears:

```tla
\* KNOWLEDGE_QUERY psi: K(0, K(1, received[1]) \/ K(2, received[2]))
```

### Knowledge Properties (Temporal Assertions)

Assert that a temporal epistemic property holds across the whole spec. The tool reports
pass/fail and exits non-zero on failure. Must use a temporal operator (`[]`, `<>`, or `~>`):

```tla
\* KNOWLEDGE_PROPERTY [](K(0, w[0]) \/ K(0, ~w[0]))
\* KNOWLEDGE_PROPERTY <>K(0, v[0])
\* KNOWLEDGE_PROPERTY sent[1] ~> K(1, received[1])
```

### Knowledge Preconditions (Label-Based Assertions)

Assert that a knowledge condition holds whenever a specific PlusCal label is active. This
verifies knowledge-based protocols: the protocol only takes an action when the agent has the
required knowledge (Halpern & Moses Section 14).

```tla
\* KNOWLEDGE_PRECONDITION AcknowledgeCommand: K(0, K(1, received[1]) \/ K(2, received[2]))
```

This checks: at every state where `pc[Leader] = "AcknowledgeCommand"`, the leader knows that
some follower knows about the log entry. The tool reports pass/fail and exits non-zero on
failure, like `KNOWLEDGE_PROPERTY`.

### Node Labels

Custom node label formatting using Python f-string syntax:

```tla
\* NODE_LABEL acks: {acks}\nreceived: {received}\nsent: {sent}
```

Template variables are state variables (excluding `pc`). Set-process local vars are
automatically converted from lists to agent-keyed dicts (e.g., `{1: True, 2: False}`).
Use `\n` for line breaks. Arbitrary Python expressions are supported inside `{}`.

### Running

```bash
.venv/bin/python3 analyze.py raft/SimpleRaft.tla
```

## Every Atomic Step Must Change a Process-Local Variable

PlusCal compiles each labeled step into a TLA+ action that updates the `pc` (program counter)
variable. The knowledge analysis ignores `pc` — it only considers process-local variables
when determining which states are indistinguishable to an agent.

If a labeled step changes only `pc` (or only global variables) without changing any process-local
variable, the state graph will contain distinct states that look identical to every agent. This
produces duplicate nodes in the indistinguishability graph and corrupts the epistemic analysis.

**Rule: every labeled step must assign to at least one process-local variable.** The exception is
the final step that transitions a process to `Done` — PlusCal termination steps that don't change
local state are allowed.

The `validate_state_transitions()` function in `lib/kripke.py` checks this and raises
`AssertionError` if any non-termination transition violates it.

### Common Violations and Fixes

**`await` / guard on its own label.** A step that only waits for a condition, then advances to the
next label:

```pluscal
\* BAD: WaitForEntry changes only pc
WaitForEntry:
    await [type |-> "send", dest |-> self] \in network;
ReceiveAndAck:
    received := TRUE;
    network := network \union {[type |-> "ack", src |-> self]};
```

Fix: merge the guard into the step that does the assignment:

```pluscal
\* GOOD: single step with guard + assignment
ReceiveAndAck:
    await [type |-> "send", dest |-> self] \in network;
    received := TRUE;
    network := network \union {[type |-> "ack", src |-> self]};
```

**`skip` or `either/or skip`.** A step that does nothing (or nondeterministically does nothing):

```pluscal
\* BAD: skip iteration changes only pc
LeaderLoop:
    while TRUE do
        either
            with f \in Followers do
                network := network \union {[type |-> "send", dest |-> f]};
                sent[f] := TRUE;
            end with;
        or
            skip;
        end either;
    end while;
```

Fix: restructure so each step assigns to a local variable:

```pluscal
\* GOOD: each step assigns to sent
SendFirst:
    with f \in Followers do
        network := network \union {[type |-> "send", dest |-> f]};
        sent[f] := TRUE;
    end with;
SendSecond:
    with f \in {f \in Followers : ~sent[f]} do
        network := network \union {[type |-> "send", dest |-> f]};
        sent[f] := TRUE;
    end with;
```

## Controller Pattern (Simultaneous Transitions)

Some puzzles require all agents to transition simultaneously — e.g. the muddy children puzzle, where
the father's question and all children's responses are a single atomic event. PlusCal's interleaving
semantics (`\E self \in ProcSet: ...`) cannot model this with one process per agent.

For these specs, use a **controller process** that atomically updates all agents' state in a single
step. The analysis script must define agents and their local state manually instead of using
`pcal.py`'s automatic mapping. See `muddy-children/muddy-children-knowledge-analysis.py` for an
example.
