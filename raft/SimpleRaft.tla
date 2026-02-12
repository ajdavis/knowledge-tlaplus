--------------------------- MODULE SimpleRaft ---------------------------
(***************************************************************************)
(* Simplified Raft for epistemic logic analysis.                           *)
(*                                                                         *)
(* - One log entry, permanent leader, two followers                        *)
(* - Agent views: Leader sees a (acks), Followers see their own r          *)
(*                                                                         *)
(* Facts to analyze:                                                       *)
(* - φ (phi): the log entry exists (on some node)                          *)
(* - ψ (psi): the log entry is majority-replicated (durable)               *)
(***************************************************************************)

EXTENDS Naturals, FiniteSets

Leader == 0
Followers == {1, 2}
Nodes == {Leader} \union Followers

(* --algorithm SimpleRaft
variables
    \* Variables listed here are indexed by agent ID for knowledge analysis
    AGENT_STATES = <<"a", "r">>,
    \* r[n] = what agent n knows about who has the entry
    \*   r[0] = TRUE (leader always has it)
    \*   r[f] = whether follower f has received
    r = [n \in Nodes |-> n = Leader],
    \* a[n] = what agent n knows about acks
    \*   a[0] = <<ack from 1, ack from 2>>
    \*   a[f] = <<>> (followers don't know about acks)
    a = [n \in Nodes |-> IF n = Leader THEN <<FALSE, FALSE>> ELSE <<>>];

\* Leader sends the log entry to each follower, order is nondeterministic
process LeaderProc = Leader
begin
    SendFirst:
        with f \in Followers do
            r[f] := TRUE;
        end with;
    SendSecond:
        with f \in {f \in Followers : ~r[f]} do
            r[f] := TRUE;
        end with;
end process;

\* Each follower acknowledges once it has received the entry
process FollowerProc \in Followers
begin
    Acknowledge:
        await r[self];
        a[Leader] := IF self = 1
                     THEN <<TRUE, a[Leader][2]>>
                     ELSE <<a[Leader][1], TRUE>>;
end process;

end algorithm; *)

\* BEGIN TRANSLATION
VARIABLES AGENT_STATES, r, a, pc

vars == << AGENT_STATES, r, a, pc >>

ProcSet == {Leader} \cup (Followers)

Init == (* Global variables *)
        /\ AGENT_STATES = <<"a", "r">>
        /\ r = [n \in Nodes |-> n = Leader]
        /\ a = [n \in Nodes |-> IF n = Leader THEN <<FALSE, FALSE>> ELSE <<>>]
        /\ pc = [self \in ProcSet |-> CASE self = Leader -> "SendFirst"
                                        [] self \in Followers -> "Acknowledge"]

SendFirst == /\ pc[Leader] = "SendFirst"
             /\ \E f \in Followers:
                  r' = [r EXCEPT ![f] = TRUE]
             /\ pc' = [pc EXCEPT ![Leader] = "SendSecond"]
             /\ UNCHANGED << AGENT_STATES, a >>

SendSecond == /\ pc[Leader] = "SendSecond"
              /\ \E f \in {f \in Followers : ~r[f]}:
                   r' = [r EXCEPT ![f] = TRUE]
              /\ pc' = [pc EXCEPT ![Leader] = "Done"]
              /\ UNCHANGED << AGENT_STATES, a >>

LeaderProc == SendFirst \/ SendSecond

Acknowledge(self) == /\ pc[self] = "Acknowledge"
                     /\ r[self]
                     /\ a' = [a EXCEPT ![Leader] = IF self = 1
                                                   THEN <<TRUE, a[Leader][2]>>
                                                   ELSE <<a[Leader][1], TRUE>>]
                     /\ pc' = [pc EXCEPT ![self] = "Done"]
                     /\ UNCHANGED << AGENT_STATES, r >>

FollowerProc(self) == Acknowledge(self)

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
