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
    \* Variables listed here are indexed by agent ID for knowledge analysis
    AGENT_STATES = <<"seesMuddy", "saidYes", "m", "q">>,
    \* muddy[i] = TRUE iff child i has mud (never changes, not directly visible to i)
    muddy \in {f \in [Children -> BOOLEAN] : \E i \in Children : f[i]},
    \* seesMuddy[i] = set of muddy children visible to i (initialized, never changes)
    seesMuddy = [i \in Children |-> {j \in Children : j /= i /\ muddy[j]}],
    \* saidYes[i] = set of children who said yes (same for all i, public)
    saidYes = [i \in Children |-> {}],
    \* m[i] = father's announcement (same for all i, public)
    m = [i \in Children |-> TRUE],
    \* q[i] = number of completed rounds (same for all i, public)
    q = [i \in Children |-> 0];

define
    \* Who says yes this round: child i says yes if they see exactly q other muddy children
    SaysYes(i) == m[i] /\ q[i] + 1 = Cardinality(seesMuddy[i]) + 1
end define;

process AskLoop = 0
begin
    Ask:
        while q[1] < N-1 do
            \* Father asks, update q and saidYes for all children
            q := [i \in Children |-> q[i] + 1] ||
            saidYes := [i \in Children |-> saidYes[i] \union {j \in Children : SaysYes(j)}];
        end while;
end process;

end algorithm; *)

\* BEGIN TRANSLATION
VARIABLES AGENT_STATES, muddy, seesMuddy, saidYes, m, q, pc

(* define statement *)
SaysYes(i) == m[i] /\ q[i] + 1 = Cardinality(seesMuddy[i]) + 1


vars == << AGENT_STATES, muddy, seesMuddy, saidYes, m, q, pc >>

ProcSet == {0}

Init == (* Global variables *)
        /\ AGENT_STATES = <<"seesMuddy", "saidYes", "m", "q">>
        /\ muddy \in {f \in [Children -> BOOLEAN] : \E i \in Children : f[i]}
        /\ seesMuddy = [i \in Children |-> {j \in Children : j /= i /\ muddy[j]}]
        /\ saidYes = [i \in Children |-> {}]
        /\ m = [i \in Children |-> TRUE]
        /\ q = [i \in Children |-> 0]
        /\ pc = [self \in ProcSet |-> "Ask"]

Ask == /\ pc[0] = "Ask"
       /\ IF q[1] < N-1
             THEN /\ /\ q' = [i \in Children |-> q[i] + 1]
                     /\ saidYes' = [i \in Children |-> saidYes[i] \union {j \in Children : SaysYes(j)}]
                  /\ pc' = [pc EXCEPT ![0] = "Ask"]
             ELSE /\ pc' = [pc EXCEPT ![0] = "Done"]
                  /\ UNCHANGED << saidYes, q >>
       /\ UNCHANGED << AGENT_STATES, muddy, seesMuddy, m >>

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
