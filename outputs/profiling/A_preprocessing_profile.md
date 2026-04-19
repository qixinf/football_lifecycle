
# A Preprocessing Profile

## Scope
This profiling pass covers:
- raw data loading
- table cleaning
- backbone merge
- vectorized age construction

## End-to-end runtime
38.81 seconds

## Main bottleneck
The dominant preprocessing bottleneck in the A-stage pipeline is the performance-table cleaning step, which is expected because the performance table is the largest of the three core inputs.

In the first cProfile pass, the full A-stage pipeline ran in about 38.8 seconds. The largest cumulative-cost function was clean_performances() at about 23.8 seconds, followed by CSV loading at about 7.1 seconds and lifecycle backbone construction at about 4.1 seconds.

## Early optimizations already applied
- vectorized age calculation
- reduced column set after cleaning
- categorical encoding for broad_position
- nullable integer types for performance metrics
- avoidance of row-wise Python loops in backbone construction

## Interpretation
These results suggest that the first-stage optimization priority should remain focused on large-table preprocessing and column-wise cleaning efficiency rather than on the backbone merge itself. The backbone construction step is nontrivial but not the dominant cost at this stage.

## Note
This profiling note should be handed to D for integration into the final technical execution summary.
