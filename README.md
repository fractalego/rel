* 20dim embeddings seem to be too low for ~60 relations.

* unconnected graphs seem to confuse the system. actually, every graph bigger than the match seem to confuse the system.
  The edges are trained correctly though. Maybe if the edges could sort of attach to the target and break the symmetry it would work.


If data < rules:
    ### Why does it not predict with all the rules?
    ### It probably means there are a few competing outputs. Use them all ?

if cannot train:
    ### MORE RULES ARE NEEDED, LOOK AT DATA 3

    ### Is shift in range of 10 enough?



The longes sentence has 70 nodes: in utils.py you should set > 70

Training
    * dgt.fit(epochs=20, step=1e-2, relaxation_epochs=200, relaxation_step=1e-3)
      50 facts
      only produces two rule with 0 recall

    * dgt.fit(epochs=20, step=1e-2, relaxation_epochs=100, relaxation_step=1e-2)
      10 facts
      two rules with 20% recall.
      I suspect the other facts are not learned from because there is no correct hypothesis

    * * dgt.fit(epochs=20, step=1e-2, relaxation_epochs=200, relaxation_step=1e-2)
      10 facts
      two rules with 40% recall.
      I had previously added a "x *(v), *(v, a4), *(a4)"
      There was a problem with the length of _max_items_size