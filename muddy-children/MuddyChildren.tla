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
    \* muddy[i] = TRUE iff child i has mud (never changes, not directly visible to i)
    \* Only "prefix" configurations: children 1..k are muddy for some k in 1..N
    muddy \in {[i \in Children |-> i <= k] : k \in Children},
    \* seesMuddy[i] = set of muddy children visible to i (initialized, never changes)
    seesMuddy = [i \in Children |-> {j \in Children : j /= i /\ muddy[j]}],
    \* saidYes[i] = set of children who said yes (same for all i, public)
    saidYes = [i \in Children |-> {}],
    \* m[i] = father's announcement (same for all i, public)
    m = [i \in Children |-> TRUE],
    \* q[i] = number of completed rounds (same for all i, public)
    q = [i \in Children |-> 0];

define
    \* Muddy child i says yes when the round matches the number of muddy children they see.
    \* q has already been incremented by the Ask step, so compare to cardinality + 1.
    SaysYes(i) == muddy[i] /\ m[i] /\ q[i] = Cardinality(seesMuddy[i]) + 1
end define;

process AskLoop = 0
begin
    Ask:
        while q[1] < N do
            \* Father asks "do you know if you have mud?"
            q := [i \in Children |-> q[i] + 1];
        Answer:
            \* Children answer simultaneously
            saidYes := [i \in Children |-> saidYes[i] \union {j \in Children : SaysYes(j)}];
        end while;
end process;

end algorithm; *)

\* BEGIN TRANSLATION
VARIABLES muddy, seesMuddy, saidYes, m, q, pc

(* define statement *)
SaysYes(i) == muddy[i] /\ m[i] /\ q[i] = Cardinality(seesMuddy[i]) + 1


vars == << muddy, seesMuddy, saidYes, m, q, pc >>

ProcSet == {0}

Init == (* Global variables *)
        /\ muddy \in {[i \in Children |-> i <= k] : k \in Children}
        /\ seesMuddy = [i \in Children |-> {j \in Children : j /= i /\ muddy[j]}]
        /\ saidYes = [i \in Children |-> {}]
        /\ m = [i \in Children |-> TRUE]
        /\ q = [i \in Children |-> 0]
        /\ pc = [self \in ProcSet |-> "Ask"]

Ask == /\ pc[0] = "Ask"
       /\ IF q[1] < N
             THEN /\ q' = [i \in Children |-> q[i] + 1]
                  /\ pc' = [pc EXCEPT ![0] = "Answer"]
             ELSE /\ pc' = [pc EXCEPT ![0] = "Done"]
                  /\ q' = q
       /\ UNCHANGED << muddy, seesMuddy, saidYes, m >>

Answer == /\ pc[0] = "Answer"
          /\ saidYes' = [i \in Children |-> saidYes[i] \union {j \in Children : SaysYes(j)}]
          /\ pc' = [pc EXCEPT ![0] = "Ask"]
          /\ UNCHANGED << muddy, seesMuddy, m, q >>

AskLoop == Ask \/ Answer

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == /\ \A self \in ProcSet: pc[self] = "Done"
               /\ UNCHANGED vars

Next == AskLoop
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(\A self \in ProcSet: pc[self] = "Done")

\* END TRANSLATION

=============================================================================
