----------------------- MODULE CoordinatedAttack -----------------------
(***************************************************************************)
(* Coordinated attack problem (Halpern & Moses Section 4, p.8):           *)
(* Two generals communicate via unreliable messenger to coordinate an     *)
(* attack. Messages may be lost. Common knowledge is unattainable with    *)
(* unreliable communication, no matter how many rounds.                   *)
(*                                                                        *)
(* Each general tracks messages sent and received. General 0 sends the    *)
(* first message; then both follow the same recv-send loop.               *)
(*                                                                        *)
(* Agent-observable state = PlusCal process-local variables: (sent, rcvd) *)
(***************************************************************************)

EXTENDS Naturals

CONSTANT Rounds

Generals == {0, 1}

(* --algorithm CoordinatedAttack

variables network = {};

process Gen \in Generals
variables sent = 0, rcvd = 0;
begin
    Step:
        while sent < Rounds do
            if self = 0 /\ sent = 0 then
                \* General 0 initiates. Message might be lost in transit.
                with arrives \in {0, 1} do
                    if arrives = 1 then
                        network := network \union {[to |-> 1]};
                    end if;
                end with;
                sent := 1;
            else
                \* Receive message, send reply which might be lost in transit.
                await [to |-> self] \in network;
                rcvd := rcvd + 1;
                sent := sent + 1;
                with arrives \in {0, 1} do
                    if arrives = 1 then
                        network := (network \ {[to |-> self]}) \union {[to |-> 1 - self]};
                    else
                        network := network \ {[to |-> self]};
                    end if;
                end with;
            end if;
        end while;
end process;

end algorithm; *)

\* NODE_LABEL 0: (s={sent[0]}, r={rcvd[0]})\n1: (s={sent[1]}, r={rcvd[1]})
\* KNOWLEDGE_QUERY K(0, rcvd[1])
\* KNOWLEDGE_QUERY K(1, rcvd[1])
\* KNOWLEDGE_QUERY K(1, K(0, rcvd[1]))
\* KNOWLEDGE_QUERY K(0, K(1, K(0, rcvd[1])))
\* KNOWLEDGE_QUERY C(rcvd[1])
\* KNOWLEDGE_PROPERTY []~C(rcvd[1])

\* BEGIN TRANSLATION
VARIABLES network, pc, sent, rcvd

vars == << network, pc, sent, rcvd >>

ProcSet == (Generals)

Init == (* Global variables *)
        /\ network = {}
        (* Process Gen *)
        /\ sent = [self \in Generals |-> 0]
        /\ rcvd = [self \in Generals |-> 0]
        /\ pc = [self \in ProcSet |-> "Step"]

Step(self) == /\ pc[self] = "Step"
              /\ IF sent[self] < Rounds
                    THEN /\ IF self = 0 /\ sent[self] = 0
                               THEN /\ \E arrives \in {0, 1}:
                                         IF arrives = 1
                                            THEN /\ network' = (network \union {[to |-> 1]})
                                            ELSE /\ TRUE
                                                 /\ UNCHANGED network
                                    /\ sent' = [sent EXCEPT ![self] = 1]
                                    /\ rcvd' = rcvd
                               ELSE /\ [to |-> self] \in network
                                    /\ rcvd' = [rcvd EXCEPT ![self] = rcvd[self] + 1]
                                    /\ sent' = [sent EXCEPT ![self] = sent[self] + 1]
                                    /\ \E arrives \in {0, 1}:
                                         IF arrives = 1
                                            THEN /\ network' = ((network \ {[to |-> self]}) \union {[to |-> 1 - self]})
                                            ELSE /\ network' = network \ {[to |-> self]}
                         /\ pc' = [pc EXCEPT ![self] = "Step"]
                    ELSE /\ pc' = [pc EXCEPT ![self] = "Done"]
                         /\ UNCHANGED << network, sent, rcvd >>

Gen(self) == Step(self)

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == /\ \A self \in ProcSet: pc[self] = "Done"
               /\ UNCHANGED vars

Next == (\E self \in Generals: Gen(self))
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(\A self \in ProcSet: pc[self] = "Done")

\* END TRANSLATION

=============================================================================
