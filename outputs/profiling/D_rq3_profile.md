# D RQ3 Profiling Note

## Pipeline
RQ3 decline slope computation over backbone (836,635 rows, 58,944 players).

## Runtime
Full pipeline: 0.54s

## Bottleneck identified
The per-player slope estimation is the core computation.  
**Baseline** (`groupby.apply` + `scipy.stats.linregress`): 2.24s  
**Optimized** (vectorized closed-form OLS via groupby aggregations): 0.05s  
**Speedup: 47.0x**

## Optimization strategy
Replaced Python-level iteration (groupby.apply calling linregress per player) with
a single pass of vectorized pandas aggregations using the closed-form OLS formula:

    slope = (n * Σxy - Σx * Σy) / (n * Σx² - (Σx)²)

Pre-computing `x_sq` and `xy` as new columns before groupby avoids repeated
element-wise operations inside the apply loop. All computation stays in
numpy/pandas vectorized paths.

## cProfile top functions
```
         40269 function calls (39479 primitive calls) in 0.528 seconds

   Ordered by: cumulative time
   List reduced from 1050 to 20 due to restriction <20>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        2    0.000    0.000    0.538    0.269 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/IPython/core/interactiveshell.py:3543(run_code)
        2    0.000    0.000    0.538    0.269 {built-in method builtins.exec}
        1    0.027    0.027    0.528    0.528 /Users/fqxin/Desktop/1019_Py/football_lifecycle/src/d_rq3_decline_utils.py:153(d_pipeline_optimized)
        6    0.001    0.000    0.170    0.028 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/groupby.py:1898(_agg_general)
        6    0.000    0.000    0.169    0.028 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/groupby.py:1964(_cython_agg_general)
       27    0.000    0.000    0.166    0.006 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/groupby.py:1978(array_func)
       27    0.000    0.000    0.166    0.006 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/ops.py:821(_cython_operation)
        2    0.000    0.000    0.156    0.078 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/internals/managers.py:1469(grouped_reduce)
       26    0.000    0.000    0.156    0.006 /Users/fqxin/Desktop/1019_Py/
```
