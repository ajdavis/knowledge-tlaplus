---------------------------- MODULE BadSpec ----------------------------
(***************************************************************************)
(* Minimal spec that violates the knowledge analysis rule: the Wait step  *)
(* changes only pc, not any AGENT_STATES variable.                        *)
(***************************************************************************)

EXTENDS Naturals

(* --algorithm BadSpec
variables
    AGENT_STATES = <<"x">>,
    x = [n \in {1, 2} |-> 0];

process Proc \in {1, 2}
begin
    Wait:
        skip;
    DoWork:
        x[self] := 1;
end process;

end algorithm; *)

\* BEGIN TRANSLATION
VARIABLES AGENT_STATES, x, pc

vars == << AGENT_STATES, x, pc >>

ProcSet == ({1, 2})

Init == (* Global variables *)
        /\ AGENT_STATES = <<"x">>
        /\ x = [n \in {1, 2} |-> 0]
        /\ pc = [self \in ProcSet |-> "Wait"]

Wait(self) == /\ pc[self] = "Wait"
              /\ TRUE
              /\ pc' = [pc EXCEPT ![self] = "DoWork"]
              /\ UNCHANGED << AGENT_STATES, x >>

DoWork(self) == /\ pc[self] = "DoWork"
                /\ x' = [x EXCEPT ![self] = 1]
                /\ pc' = [pc EXCEPT ![self] = "Done"]
                /\ UNCHANGED AGENT_STATES

Proc(self) == Wait(self) \/ DoWork(self)

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == /\ \A self \in ProcSet: pc[self] = "Done"
               /\ UNCHANGED vars

Next == (\E self \in {1, 2}: Proc(self))
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(\A self \in ProcSet: pc[self] = "Done")

\* END TRANSLATION

=============================================================================
