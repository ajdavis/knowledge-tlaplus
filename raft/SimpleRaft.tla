--------------------------- MODULE SimpleRaft ---------------------------
(***************************************************************************)
(* Simplified Raft for epistemic logic analysis.                           *)
(*                                                                         *)
(* - One log entry, permanent leader, two followers                        *)
(* - Communication via a global network (set of messages)                  *)
(* - Agent-observable state = PlusCal process-local variables              *)
(*   Leader sees: sent, acks    Follower sees: received                    *)
(***************************************************************************)

EXTENDS Naturals

Leader == 0
Followers == {1, 2}
Nodes == {Leader} \union Followers

(* --algorithm SimpleRaft
variables
    network = {};

process LeaderProc = Leader
variables
    sent = [f \in Followers |-> FALSE],
    acks = [f \in Followers |-> FALSE];
begin
    SendFirst:
        with f \in Followers do
            network := network \union {[type |-> "send", dest |-> f]};
            sent[f] := TRUE;
        end with;
    SendSecond:
        with f \in {f \in Followers : ~sent[f]} do
            network := network \union {[type |-> "send", dest |-> f]};
            sent[f] := TRUE;
        end with;
    ReceiveAck1:
        with f \in {f \in Followers : [type |-> "ack", src |-> f] \in network /\ ~acks[f]} do
            acks[f] := TRUE;
        end with;
    ReceiveAck2:
        with f \in {f \in Followers : [type |-> "ack", src |-> f] \in network /\ ~acks[f]} do
            acks[f] := TRUE;
        end with;
end process;

process FollowerProc \in Followers
variable received = FALSE;
begin
    ReceiveAndAck:
        await [type |-> "send", dest |-> self] \in network;
        received := TRUE;
        network := network \union {[type |-> "ack", src |-> self]};
end process;

end algorithm; *)

\* BEGIN TRANSLATION
VARIABLES network, pc, sent, acks, received

vars == << network, pc, sent, acks, received >>

ProcSet == {Leader} \cup (Followers)

Init == (* Global variables *)
        /\ network = {}
        (* Process LeaderProc *)
        /\ sent = [f \in Followers |-> FALSE]
        /\ acks = [f \in Followers |-> FALSE]
        (* Process FollowerProc *)
        /\ received = [self \in Followers |-> FALSE]
        /\ pc = [self \in ProcSet |-> CASE self = Leader -> "SendFirst"
                                        [] self \in Followers -> "ReceiveAndAck"]

SendFirst == /\ pc[Leader] = "SendFirst"
             /\ \E f \in Followers:
                  /\ network' = (network \union {[type |-> "send", dest |-> f]})
                  /\ sent' = [sent EXCEPT ![f] = TRUE]
             /\ pc' = [pc EXCEPT ![Leader] = "SendSecond"]
             /\ UNCHANGED << acks, received >>

SendSecond == /\ pc[Leader] = "SendSecond"
              /\ \E f \in {f \in Followers : ~sent[f]}:
                   /\ network' = (network \union {[type |-> "send", dest |-> f]})
                   /\ sent' = [sent EXCEPT ![f] = TRUE]
              /\ pc' = [pc EXCEPT ![Leader] = "ReceiveAck1"]
              /\ UNCHANGED << acks, received >>

ReceiveAck1 == /\ pc[Leader] = "ReceiveAck1"
               /\ \E f \in {f \in Followers : [type |-> "ack", src |-> f] \in network /\ ~acks[f]}:
                    acks' = [acks EXCEPT ![f] = TRUE]
               /\ pc' = [pc EXCEPT ![Leader] = "ReceiveAck2"]
               /\ UNCHANGED << network, sent, received >>

ReceiveAck2 == /\ pc[Leader] = "ReceiveAck2"
               /\ \E f \in {f \in Followers : [type |-> "ack", src |-> f] \in network /\ ~acks[f]}:
                    acks' = [acks EXCEPT ![f] = TRUE]
               /\ pc' = [pc EXCEPT ![Leader] = "Done"]
               /\ UNCHANGED << network, sent, received >>

LeaderProc == SendFirst \/ SendSecond \/ ReceiveAck1 \/ ReceiveAck2

ReceiveAndAck(self) == /\ pc[self] = "ReceiveAndAck"
                       /\ [type |-> "send", dest |-> self] \in network
                       /\ received' = [received EXCEPT ![self] = TRUE]
                       /\ network' = (network \union {[type |-> "ack", src |-> self]})
                       /\ pc' = [pc EXCEPT ![self] = "Done"]
                       /\ UNCHANGED << sent, acks >>

FollowerProc(self) == ReceiveAndAck(self)

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == /\ \A self \in ProcSet: pc[self] = "Done"
               /\ UNCHANGED vars

Next == LeaderProc
           \/ (\E self \in Followers: FollowerProc(self))
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(\A self \in ProcSet: pc[self] = "Done")

\* END TRANSLATION

=============================================================================
