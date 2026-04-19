# D RQ3 Profiling Note

## Pipeline
RQ3 decline slope computation over backbone (836,635 rows, 58,944 players).

## Runtime
Full pipeline: 0.42s

## Bottleneck identified
The per-player slope estimation is the core computation.  
**Baseline** (`groupby.apply` + `scipy.stats.linregress`): 1.98s  
**Optimized** (vectorized closed-form OLS via groupby aggregations): 0.04s  
**Speedup: 44.3x**

## Optimization strategy
Replaced Python-level iteration (groupby.apply calling linregress per player) with
a single pass of vectorized pandas aggregations using the closed-form OLS formula:

    slope = (n * Σxy - Σx * Σy) / (n * Σx² - (Σx)²)

Pre-computing `x_sq` and `xy` as new columns before groupby avoids repeated
element-wise operations inside the apply loop. All computation stays in
numpy/pandas vectorized paths.

## cProfile top functions
```
         44420 function calls (43506 primitive calls) in 0.422 seconds

   Ordered by: cumulative time
   List reduced from 1036 to 20 due to restriction <20>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        2    0.000    0.000    0.422    0.211 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/IPython/core/interactiveshell.py:3543(run_code)
        2    0.000    0.000    0.422    0.211 {built-in method builtins.exec}
        1    0.004    0.004    0.422    0.422 /var/folders/_j/__475r_x6hs0kv9nsh3rt4c40000gn/T/ipykernel_14936/1622116549.py:1(<module>)
        1    0.021    0.021    0.418    0.418 /Users/fqxin/Desktop/1019_Py/football_lifecycle/src/d_rq3_decline_utils.py:117(compute_all_decline_metrics)
        1    0.004    0.004    0.116    0.116 /Users/fqxin/Desktop/1019_Py/football_lifecycle/src/d_rq3_decline_utils.py:39(extract_post_peak_data)
        8    0.000    0.000    0.111    0.014 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/groupby.py:1964(_cython_agg_general)
       19    0.000    0.000    0.109    0.006 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/groupby.py:1978(array_func)
       19    0.000    0.000    0.109    0.006 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/ops.py:821(_cython_operation)
    18/16    0.003    0.000    0.098    0.006 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-package
```
