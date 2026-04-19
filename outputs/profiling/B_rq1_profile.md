# B RQ1 Profiling Note

## Pipeline
Peak age computation over backbone (836,635 rows, 58,944 players).

## Benchmark
| Method | Runtime (s) | Output rows |
|---|---|---|
| naive_groupby_apply | 9.613 | 58,944 |
| optimized_peak_flag | 0.060 | 58,944 |

Speedup: **161.2x**

## Optimization strategy
The naive approach scans every player group to find the max market value row.
The optimized version filters on the precomputed `is_peak_value_obs` flag once,
then uses a single sorted groupby.first() — no Python-level per-group iteration.

## cProfile top functions
```
         7329 function calls (7220 primitive calls) in 0.121 seconds

   Ordered by: cumulative time
   List reduced from 635 to 15 due to restriction <15>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        2    0.000    0.000    0.121    0.061 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/IPython/core/interactiveshell.py:3543(run_code)
        2    0.000    0.000    0.121    0.061 {built-in method builtins.exec}
        1    0.008    0.008    0.121    0.121 /var/folders/_j/__475r_x6hs0kv9nsh3rt4c40000gn/T/ipykernel_26932/2722590097.py:1(<module>)
        1    0.010    0.010    0.114    0.114 /Users/fqxin/Desktop/1019_Py/football_lifecycle/src/b_rq1_peak_age_utils.py:15(compute_peak_age)
        1    0.000    0.000    0.036    0.036 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/groupby.py:3344(first)
        1    0.000    0.000    0.036    0.036 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/groupby.py:1898(_agg_general)
        1    0.000    0.000    0.036    0.036 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/groupby.py:1964(_cython_agg_general)
        1    0.000    0.000    0.035    0.035 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/internals/managers.py:1469(grouped_reduce)
       11    0.000    0.000    0.035    0.003 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/
```
