(* The "Muddy Children" puzzle from the 1990 paper "Knowledge and common knowledge in a *)
(* distributed environment" *)
---- MODULE MuddyChildren ----

EXTENDS Naturals, Integers, Sequences

CONSTANT n \* Total number of children
ASSUME n \in Nat
CONSTANT m \* Whether father said "at least one of you has mud on your head" at the start.
ASSUME m \in BOOLEAN
VARIABLE k \* Number of muddy children.
VARIABLE q \* Number of times father asked, "Can any of you prove you have mud on your head?".
\* VARIABLE kRanges
VARIABLE history \* Sequence of observations by the children.

vars == <<k, q, history>>

TypeOK == m \in BOOLEAN /\ k \in Int /\ q \in Int

IsMuddy(i) == i <= k \* Say arbitrarily that the first k children are muddy
MuddyChildrenSeenBy(i) == IF IsMuddy(i) THEN k - 1 ELSE k
CanProveMuddy(i) == q > MuddyChildrenSeenBy(i) /\ m \* The correct test, from the paper
ThinksMuddy(i) == q > MuddyChildrenSeenBy(i) \* Test what happens without "m" condition

\* A record of what child i saw in this state.
MakeHistoryEntry(i) == [q |-> q, muddyChildrenSeen |-> MuddyChildrenSeenBy(i), m |-> m]


\* assume i is muddy
\* n=0, lo=MuddyChildrenSeenBy(i), hi=MuddyChildrenSeenBy(i)+1
\* n=1, lo=MuddyChildrenSeenBy(i)-1 since it doesn't see itself and i might be clean
\*      hi=MuddyChildrenSeenBy(i)+1 since i might be muddy
\* RECURSIVE IndirectKnowledgeOfK(_, _)
\* IndirectKnowledgeOfK(n, i) ==
\*   IF n = 0 THEN
\*     LET iKnow == [
\*       lo -> MuddyChildrenSeenBy(i),     \* I directly see this many muddy children
\*       hi -> MuddyChildrenSeenBy(i) + 1  \* I might also be muddy
\*     ], nextKnows == IndirectKnowledgeOfK(n + 1, i)
\*     IN [lo |-> iKnow.lo, hi |-> iKnow.hi]
\*   ELSE
\*     IN [lo |-> MuddyChildrenSeenBy(i), hi |-> prev.hi]



Init == 
  \* Some number of muddy children.
  /\ k \in 0..n
  \* If there are any muddy children, the father *might* say so.
  /\ m \in (IF k > 0 THEN BOOLEAN ELSE {FALSE})
  \* Initially the father has asked the question zero times.
  /\ q = 0
  \* /\ kRanges = [i \in 1..n |-> 
  /\ history = <<>>

Next == 
  \* The next action is father asking the question again.
  /\ q' = q + 1 
  \* Each child records its history in this state.
  /\ history' = Append(history, [i \in 1..n |-> MakeHistoryEntry(i)])
  \* Gotta stop somewhere. Disable deadlock checking or this causes an error.
  /\ q < n
  /\ UNCHANGED k

Spec == Init /\ [][Next]_vars


=============================
