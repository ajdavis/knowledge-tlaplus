--------------------------- MODULE MuddyChildren ---------------------------
(***************************************************************************)
(* Muddy children puzzle from Halpern & Moses, "Knowledge and Common       *)
(* Knowledge in a Distributed Environment", Section 2.                     *)
(*                                                                         *)
(* n children play together, k get mud on their foreheads. Each can see    *)
(* others but not themselves. Father announces "at least one of you has    *)
(* mud" then repeatedly asks "can you prove you have mud?" Children answer *)
(* simultaneously. After k-1 rounds of "no", muddy children answer "yes".  *)
(***************************************************************************)

EXTENDS Naturals, FiniteSets, TLC, Sequences

CONSTANT N

ASSUME N \in Nat

Children == 1..N

(* --algorithm MuddyChildren
variables
    \* muddy[i] = TRUE iff child i has mud on forehead
    \* When m=TRUE, at least one child must be muddy (father's announcement is true)
    muddy \in {f \in [Children -> BOOLEAN] : \E i \in Children : f[i]},
    \* m = father has announced "at least one is muddy"
    m = TRUE,
    \* q = number of completed rounds of questioning
    q = 0,
    \* saidYes[i] = TRUE iff child i has said "yes" (visible to all)
    saidYes = [i \in Children |-> FALSE];

define
    SeesMuddy(i) == {j \in Children : j /= i /\ muddy[j]}
end define;

process AskLoop = 0
begin
    Ask:
        while q < N-1 do
            \* Father asks, all children respond based on new q value
            q := q + 1 ||
            saidYes := [i \in Children |-> saidYes[i] \/ (m /\ q + 1 = Cardinality(SeesMuddy(i)) + 1)];
        end while;
end process;

end algorithm; *)

\* BEGIN TRANSLATION
VARIABLES pc, muddy, m, q, saidYes

(* define statement *)
SeesMuddy(i) == {j \in Children : j /= i /\ muddy[j]}


vars == << pc, muddy, m, q, saidYes >>

ProcSet == {0}

Init == (* Global variables *)
        /\ muddy \in {f \in [Children -> BOOLEAN] : \E i \in Children : f[i]}
        /\ m = TRUE
        /\ q = 0
        /\ saidYes = [i \in Children |-> FALSE]
        /\ pc = [self \in ProcSet |-> "Ask"]

Ask == /\ pc[0] = "Ask"
       /\ IF q < N-1
             THEN /\ /\ q' = q + 1
                     /\ saidYes' = [i \in Children |-> saidYes[i] \/ (m /\ q + 1 = Cardinality(SeesMuddy(i)) + 1)]
                  /\ pc' = [pc EXCEPT ![0] = "Ask"]
             ELSE /\ pc' = [pc EXCEPT ![0] = "Done"]
                  /\ UNCHANGED << q, saidYes >>
       /\ UNCHANGED << muddy, m >>

AskLoop == Ask

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == /\ \A self \in ProcSet: pc[self] = "Done"
               /\ UNCHANGED vars

Next == AskLoop
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(\A self \in ProcSet: pc[self] = "Done")

\* END TRANSLATION

=============================================================================
