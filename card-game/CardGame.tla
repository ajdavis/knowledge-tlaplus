--------------------------- MODULE CardGame ---------------------------
(***************************************************************************)
(* Card game from Reasoning About Knowledge, Section 2.1:                  *)
(* "Suppose that we have a deck consisting of three cards labeled A, B,    *)
(* and C. Agents 1 and 2 each get one of these cards; the third card is    *)
(* left face down."                                                        *)
(***************************************************************************)

EXTENDS Naturals, FiniteSets, TLC, Sequences

Cards == {"A", "B", "C"}
Agents == {1, 2}

\* All permutations of cards: the 6 valid deals
Deals == {<<c1, c2, c3>> \in Cards \X Cards \X Cards :
            c1 /= c2 /\ c2 /= c3 /\ c1 /= c3}

(* --algorithm CardGame
variables
    deal \in Deals;

define
    hand(agent) == deal[agent]
    table == deal[3]
end define;

process Agent \in Agents
begin
    Skip: skip
end process;

end algorithm; *)

\* BEGIN TRANSLATION (chksum(pcal) = "50a32e54" /\ chksum(tla) = "d91ed12e")
VARIABLES deal, pc

(* define statement *)
hand(agent) == deal[agent]
table == deal[3]


vars == << deal, pc >>

ProcSet == (Agents)

Init == (* Global variables *)
        /\ deal \in Deals
        /\ pc = [self \in ProcSet |-> "Skip"]

Skip(self) == /\ pc[self] = "Skip"
              /\ TRUE
              /\ pc' = [pc EXCEPT ![self] = "Done"]
              /\ deal' = deal

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
