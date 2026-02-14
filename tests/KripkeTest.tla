--------------------------- MODULE KripkeTest ---------------------------
(***************************************************************************)
(* Minimal spec for testing epistemic formula evaluation.                  *)
(*                                                                         *)
(* Two agents {0, 1}, each with a private boolean v[self] and a shared     *)
(* boolean w (set for all agents atomically). This creates disconnected    *)
(* components in the indistinguishability graph: the initial state (where   *)
(* w is all-FALSE) is distinguishable from all post-action states (where   *)
(* w is all-TRUE), giving non-trivial results for C (common knowledge).   *)
(***************************************************************************)

EXTENDS Naturals

Agents == {0, 1}

(* --algorithm KripkeTest
variables
    v = [a \in Agents |-> FALSE],
    w = [a \in Agents |-> FALSE];

process Agent \in Agents
begin
    Act:
        v[self] := TRUE;
        w := [a \in Agents |-> TRUE];
end process;

end algorithm; *)

\* BEGIN TRANSLATION
VARIABLES v, w, pc

vars == << v, w, pc >>

ProcSet == (Agents)

Init == (* Global variables *)
        /\ v = [a \in Agents |-> FALSE]
        /\ w = [a \in Agents |-> FALSE]
        /\ pc = [self \in ProcSet |-> "Act"]

Act(self) == /\ pc[self] = "Act"
             /\ v' = [v EXCEPT ![self] = TRUE]
             /\ w' = [a \in Agents |-> TRUE]
             /\ pc' = [pc EXCEPT ![self] = "Done"]

Agent(self) == Act(self)

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == /\ \A self \in ProcSet: pc[self] = "Done"
               /\ UNCHANGED vars

Next == (\E self \in Agents: Agent(self))
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(\A self \in ProcSet: pc[self] = "Done")

\* END TRANSLATION

=============================================================================
