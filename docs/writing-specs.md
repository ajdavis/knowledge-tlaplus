# Writing TLA+/PlusCal Specs for Knowledge Analysis

## AGENT_STATES Convention

Declare an `AGENT_STATES` variable listing the variable names that represent each agent's local
state. Each listed variable must be indexed by agent ID.

```tla
variables
    AGENT_STATES = <<"x", "y">>,
    x = [n \in Agents |-> ...],
    y = [n \in Agents |-> ...];
```

## Every Atomic Step Must Change an Agent-Visible Variable

PlusCal compiles each labeled step into a TLA+ action that updates the `pc` (program counter)
variable. The knowledge analysis ignores `pc` — it only considers the variables in `AGENT_STATES`
when determining which states are indistinguishable to an agent.

If a labeled step changes only `pc` and no `AGENT_STATES` variable, the state graph will contain
distinct states that look identical to every agent. This produces duplicate nodes in the
indistinguishability graph and corrupts the epistemic analysis.

**Rule: every labeled step in PlusCal must assign to at least one `AGENT_STATES` variable.**

The `validate_state_transitions()` function in `lib/knowledge.py` checks this and raises
`AssertionError` if any transition violates it.

### Common Violations and Fixes

**`await` / guard on its own label.** A step that only waits for a condition, then advances to the
next label:

```tla
\* BAD: WaitForEntry changes only pc
WaitForEntry:
    await r[self];
Acknowledge:
    a[Leader][self] := TRUE;
```

Fix: merge the guard into the step that does the assignment:

```tla
\* GOOD: single step with guard + assignment
Acknowledge:
    await r[self];
    a[Leader][self] := TRUE;
```

**`skip` or `either/or skip`.** A step that does nothing (or nondeterministically does nothing):

```tla
\* BAD: skip iteration changes only pc
LeaderLoop:
    while TRUE do
        either
            with f \in Followers do r[f] := TRUE; end with;
        or
            skip;
        end either;
    end while;
```

Fix: restructure so each step performs an assignment. For example, replace the loop with sequential
nondeterministic steps:

```tla
\* GOOD: each step assigns to r
SendFirst:
    with f \in Followers do r[f] := TRUE; end with;
SendSecond:
    with f \in {f \in Followers : ~r[f]} do r[f] := TRUE; end with;
```
