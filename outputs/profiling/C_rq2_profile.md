# C RQ2 Profiling Note

## Pipeline
RQ2 peak performance extraction from merged backbone x performance table (2,230,254 rows, 58,782 players).

## Bottleneck identified
Extracting each player's best row from the 2,230,254-row merged DataFrame.
**Baseline** (`sort_values` + `groupby.first()`): 0.859s
**Optimized** (`groupby.idxmax()`): 0.090s
**Speedup: 9.5x**

## Optimization strategy
Replaced O(n log n) `sort_values(['player_id', 'performance'])` followed by
`groupby.first()` with a single O(n) `groupby('player_id')['performance'].idxmax()`.
idxmax scans each group once to return the index of the maximum performance value;
`.loc[idx]` then retrieves those rows without sorting the full 2,230,254-row DataFrame.

## cProfile top functions (baseline peak extraction)
```
7906 function calls (7805 primitive calls) in 0.864 seconds

   Ordered by: cumulative time
   List reduced from 524 to 20 due to restriction <20>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        2    0.000    0.000    0.893    0.446 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/IPython/core/interactiveshell.py:3543(run_code)
        2    0.000    0.000    0.893    0.446 {built-in method builtins.exec}
        1    0.000    0.000    0.576    0.576 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/groupby.py:3344(first)
        1    0.000    0.000    0.576    0.576 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/groupby.py:1898(_agg_general)
        1    0.000    0.000    0.576    0.576 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/groupby.py:1964(_cython_agg_general)
        1    0.000    0.000    0.575    0.575 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/internals/managers.py:1469(grouped_reduce)
       33    0.000    0.000    0.575    0.017 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/internals/blocks.py:389(apply)
       33    0.000    0.000    0.575    0.017 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/groupby.py:1978(array_func)
       33    0.000    0.000    0.575    0.017 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/ops.py:821(_cython_operation)
       33    0.004    0.000    0.501    0.015 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/ops.py:532(cython_operation)
        8    0.000    0.000    0.394    0.049 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/arrays/base.py:2327(_groupby_op)
       33    0.000    0.000    0.316    0.010 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/ops.py:311(_cython_op_ndim_compat)
       33    0.314    0.010    0.316    0.010 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/groupby/ops.py:358(_call_cython_op)
        1    0.000    0.000    0.288    0.288 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/frame.py:7019(sort_values)
        8    0.002    0.000    0.178    0.022 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/arrays/numpy_.py:506(to_numpy)
        3    0.005    0.002    0.167    0.056 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/algorithms.py:610(factorize)
    86/37    0.000    0.000    0.166    0.004 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/array_algos/take.py:59(take_nd)
    65/64    0.000    0.000    0.165    0.003 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/dtypes/missing.py:101(isna)
    65/64    0.000    0.000    0.165    0.003 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/dtypes/missing.py:184(_isna)
       11    0.000    0.000    0.165    0.015 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/arrays/numpy_.py:237(isna)
```
