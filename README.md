* 20dim embeddings seem to be too low for ~60 relations.

* unconnected graphs seem to confuse the system. actually, every graph bigger than the match seem to confuse the system.
  The edges are trained correctly though. Maybe if the edges could sort of attach to the target and break the symmetry it would work.


If data < rules:
    ### Why does it not predict with all the rules?
    ### It probably means there are a few competing outputs. Use them all ?

if cannot train:
    ### MORE RULES ARE NEEDED, LOOK AT DATA 3

    ### Is shift in range of 10 enough?