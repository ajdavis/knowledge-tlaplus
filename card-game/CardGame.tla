--------------------------- MODULE CardGame ---------------------------
(***************************************************************************)
(* Card game from Reasoning About Knowledge, Section 2.1:                  *)
(* "Suppose that we have a deck consisting of three cards labeled A, B,    *)
(* and C. Agents 1 and 2 each get one of these cards; the third card is    *)
(* left face down."                                                        *)
(*                                                                         *)
(* Agent-observable state = PlusCal process-local variables.               *)
(* Each agent sees only their own hand (card).                             *)
(***************************************************************************)

EXTENDS Naturals, FiniteSets

Cards == {"A", "B", "C"}
Agents == {1, 2}

\* All permutations of cards: the 6 valid deals
Deals == {<<c1, c2, c3>> \in Cards \X Cards \X Cards :
            c1 /= c2 /\ c2 /= c3 /\ c1 /= c3}

(* --algorithm CardGame
variables
    deal \in Deals;

define
    table == deal[3]
end define;

process Agent \in Agents
variable hand = deal[self];
begin
    Skip: skip
end process;

end algorithm; *)

\* BEGIN TRANSLATION
VARIABLES deal, pc

(* define statement *)
table == deal[3]

VARIABLE hand

vars == << deal, pc, hand >>

ProcSet == (Agents)

Init == (* Global variables *)
        /\ deal \in Deals
        (* Process Agent *)
        /\ hand = [self \in Agents |-> deal[self]]
        /\ pc = [self \in ProcSet |-> "Skip"]

Skip(self) == /\ pc[self] = "Skip"
              /\ TRUE
              /\ pc' = [pc EXCEPT ![self] = "Done"]
              /\ UNCHANGED << deal, hand >>

Agent(self) == Skip(self)

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == /\ \A self \in ProcSet: pc[self] = "Done"
               /\ UNCHANGED vars

Next == (\E self \in Agents: Agent(self))
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(\A self \in ProcSet: pc[self] = "Done")

\* END TRANSLATION

=============================================================================
