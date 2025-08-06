(* The "Muddy Children" puzzle from the 1990 paper "Knowledge and common knowledge in a *)
(* distributed environment" *)
---- MODULE MuddyChildren ----

EXTENDS Naturals, Integers

CONSTANT n \* Total number of children
ASSUME n \in Nat
VARIABLE m \* Whether father said "at least one of you has mud on your head" at the start.
VARIABLE k \* Number of muddy children.
VARIABLE q \* Number of times father asked, "Can any of you prove you have mud on your head?".

vars == <<m, k, q>>

IsMuddy(i) == i <= k \* Say arbitrarily that the first k children are muddy
MuddyChildrenSeenBy(i) == IF IsMuddy(i) THEN k - 1 ELSE k
CanProveMuddy(i) == q > MuddyChildrenSeenBy(i) /\ m \* The correct test, from the paper
ThinksMuddy(i) == q > MuddyChildrenSeenBy(i) \* Test what happens without "m" condition

TypeOK == m \in BOOLEAN /\ k \in Int /\ q \in Int

Init == 
  \* Some number of muddy children.
  /\ k \in 0..n
  \* If there are any muddy children, the father *might* say so.
  /\ m \in (IF k > 0 THEN BOOLEAN ELSE {FALSE})
  \* Initially the father has asked the question zero times.
  /\ q = 0

Next == 
  \* The next action is father asking the question again.
  /\ q' = q + 1 
  \* Gotta stop somewhere. Disable deadlock checking or this causes an error.
  /\ q < n + 10
  /\ UNCHANGED <<m, k>>

Spec == Init /\ [][Next]_vars


=============================
