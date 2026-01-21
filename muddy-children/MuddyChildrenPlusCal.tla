(* The "Muddy Children" puzzle from the 1990 paper "Knowledge and common knowledge in a *)
(* distributed environment" *)
----------------------------- MODULE MuddyChildrenPlusCal -----------------------------

EXTENDS Naturals, Sequences

CONSTANT n \* Total number of children
ASSUME n \in Nat

(*
--algorithm MuddyChildrenPlusCal
variables 
    k \in 0..n, \* Number of muddy children.
    q = 0; \* Number of times father asked, "Can any of you prove you have mud on your head?".

define
    MuddyChildren == {i \in 1..n : muddy[i]}
end define;

process (Child \in 1..n)
variable seenMuddy;
begin
    Observe:
        seenMuddy := Cardinality({j \in 1..n : j # self /\ muddy[j]});
        if muddy[self] /\ seenMuddy = round then
            knows[self] := TRUE;
        end if;
end process;

end algorithm
*)

=============================================================================
