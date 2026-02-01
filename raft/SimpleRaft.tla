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

\* Leader sends the log entry to a follower that doesn't have it yet
process LeaderProc = Leader
begin
    LeaderLoop:
        while TRUE do
            either
                \* Send entry to a follower that doesn't have it
                with f \in {f \in Followers : ~r[f]} do
                    r[f] := TRUE;
                end with;
            or
                \* Skip (allow interleaving)
                skip;
            end either;
        end while;
end process;

\* Each follower can acknowledge once it has received the entry
process FollowerProc \in Followers
begin
    WaitForEntry:
        await r[self];
    Acknowledge:
        \* Update a[0] to reflect this ack
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
        /\ pc = [self \in ProcSet |-> CASE self = Leader -> "LeaderLoop"
                                        [] self \in Followers -> "WaitForEntry"]

LeaderLoop == /\ pc[Leader] = "LeaderLoop"
              /\ \/ /\ \E f \in {f \in Followers : ~r[f]}:
                         r' = [r EXCEPT ![f] = TRUE]
                 \/ /\ TRUE
                    /\ r' = r
              /\ pc' = [pc EXCEPT ![Leader] = "LeaderLoop"]
              /\ UNCHANGED << AGENT_STATES, a >>

LeaderProc == LeaderLoop

WaitForEntry(self) == /\ pc[self] = "WaitForEntry"
                      /\ r[self]
                      /\ pc' = [pc EXCEPT ![self] = "Acknowledge"]
                      /\ UNCHANGED << AGENT_STATES, r, a >>

Acknowledge(self) == /\ pc[self] = "Acknowledge"
                     /\ a' = [a EXCEPT ![Leader] = IF self = 1
                                                   THEN <<TRUE, a[Leader][2]>>
                                                   ELSE <<a[Leader][1], TRUE>>]
                     /\ pc' = [pc EXCEPT ![self] = "Done"]
                     /\ UNCHANGED << AGENT_STATES, r >>

FollowerProc(self) == WaitForEntry(self) \/ Acknowledge(self)

Next == LeaderProc
           \/ (\E self \in Followers: FollowerProc(self))

Spec == Init /\ [][Next]_vars

\* END TRANSLATION

=============================================================================
