--------------------------- MODULE LoginFixed ----------------------------
(***************************************************************************)
(* Traffic analysis side-channel (fixed): Alice logs into Bob's server     *)
(* while Carol eavesdrops on the encrypted channel. Carol can't read       *)
(* messages but can count them. In this fixed version, Alice always sends  *)
(* a dummy request on failure, making the count always 4.                  *)
(*                                                                         *)
(* Agents: Alice (0), Bob (1), Carol (2).                                 *)
(* Agent-observable state = PlusCal process-local variables.              *)
(***************************************************************************)

EXTENDS Integers

(* --algorithm LoginFixed

variables
    granted \in BOOLEAN,
    msgCount = 0;

process Alice = 0
variables loggedIn = FALSE, phase = 0;
begin
    Login:
        msgCount := msgCount + 2;
        loggedIn := granted;
        phase := 1;
    MaybeFetchData:
        msgCount := msgCount + 2;
        phase := 2;
end process;

process Bob = 1
variable decision = granted;
begin
    BobSkip: skip
end process;

process Carol = 2
variable observed = -1;
begin
    Observe:
        await phase = 2;
        observed := msgCount;
end process;

end algorithm; *)

\* NODE_LABEL granted: {granted}\nloggedIn: {loggedIn}\nmsgCount: {msgCount}\nobserved: {observed}
\* KNOWLEDGE_QUERY K(2, granted)
\* KNOWLEDGE_QUERY ignorance: ~K(2, granted) /\ ~K(2, ~granted)
\* KNOWLEDGE_PROPERTY [](~K(2, granted) /\ ~K(2, ~granted))
\* KNOWLEDGE_PROPERTY <>(K(0, granted) \/ K(0, ~granted))

\* BEGIN TRANSLATION
VARIABLES granted, msgCount, pc, loggedIn, phase, decision, observed

vars == << granted, msgCount, pc, loggedIn, phase, decision, observed >>

ProcSet == {0} \cup {1} \cup {2}

Init == (* Global variables *)
        /\ granted \in BOOLEAN
        /\ msgCount = 0
        (* Process Alice *)
        /\ loggedIn = FALSE
        /\ phase = 0
        (* Process Bob *)
        /\ decision = granted
        (* Process Carol *)
        /\ observed = -1
        /\ pc = [self \in ProcSet |-> CASE self = 0 -> "Login"
                                        [] self = 1 -> "BobSkip"
                                        [] self = 2 -> "Observe"]

Login == /\ pc[0] = "Login"
         /\ msgCount' = msgCount + 2
         /\ loggedIn' = granted
         /\ phase' = 1
         /\ pc' = [pc EXCEPT ![0] = "MaybeFetchData"]
         /\ UNCHANGED << granted, decision, observed >>

MaybeFetchData == /\ pc[0] = "MaybeFetchData"
                  /\ msgCount' = msgCount + 2
                  /\ phase' = 2
                  /\ pc' = [pc EXCEPT ![0] = "Done"]
                  /\ UNCHANGED << granted, loggedIn, decision, observed >>

Alice == Login \/ MaybeFetchData

BobSkip == /\ pc[1] = "BobSkip"
           /\ TRUE
           /\ pc' = [pc EXCEPT ![1] = "Done"]
           /\ UNCHANGED << granted, msgCount, loggedIn, phase, decision, 
                           observed >>

Bob == BobSkip

Observe == /\ pc[2] = "Observe"
           /\ phase = 2
           /\ observed' = msgCount
           /\ pc' = [pc EXCEPT ![2] = "Done"]
           /\ UNCHANGED << granted, msgCount, loggedIn, phase, decision >>

Carol == Observe

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == /\ \A self \in ProcSet: pc[self] = "Done"
               /\ UNCHANGED vars

Next == Alice \/ Bob \/ Carol
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(\A self \in ProcSet: pc[self] = "Done")

\* END TRANSLATION

=============================================================================
