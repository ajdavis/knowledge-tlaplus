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

## Epistemic Property Annotations

Add `KNOWLEDGE_PROPERTY` comments to the `.tla` file (before `\* BEGIN TRANSLATION`):

```tla
\* KNOWLEDGE_PROPERTY K(0, K(1, received[1]) \/ K(2, received[2]))
```

Then run `analyze.py` to evaluate them:

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
