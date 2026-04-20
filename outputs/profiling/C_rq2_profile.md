# C RQ2 Profiling Note

## Pipeline
RQ2 peak performance extraction from merged backbone x performance table (2,230,254 rows, 58,782 players).

## Bottleneck identified
Extracting each player's best row from the 2,230,254-row merged DataFrame.
**Baseline** (`sort_values` + `groupby.first()`): 1.618s
**Optimized** (`groupby.idxmax()`): 0.835s
**Speedup: 1.9x**

## Optimization strategy
Replaced O(n log n) `sort_values(['player_id', 'performance'])` followed by
`groupby.first()` with a single O(n) `groupby('player_id')['performance'].idxmax()`.
idxmax scans each group once to return the index of the maximum performance value;
`.loc[idx]` then retrieves those rows without sorting the full 2,230,254-row DataFrame.

## cProfile top functions (baseline peak extraction)
```
13021 function calls (12746 primitive calls) in 0.842 seconds

   Ordered by: cumulative time
   List reduced from 724 to 20 due to restriction <20>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        2    0.000    0.000    0.842    0.421 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/IPython/core/interactiveshell.py:3543(run_code)
        2    0.000    0.000    0.842    0.421 {built-in method builtins.exec}
        1    0.064    0.064    0.842    0.842 /var/folders/_j/__475r_x6hs0kv9nsh3rt4c40000gn/T/ipykernel_30602/1865901254.py:1(<module>)
        1    0.002    0.002    0.778    0.778 /var/folders/_j/__475r_x6hs0kv9nsh3rt4c40000gn/T/ipykernel_30602/1865901254.py:2(c_optimized)
        1    0.018    0.018    0.562    0.562 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/frame.py:10840(merge)
        1    0.001    0.001    0.544    0.544 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/reshape/merge.py:135(merge)
        1    0.046    0.046    0.494    0.494 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/reshape/merge.py:882(get_result)
        1    0.000    0.000    0.283    0.283 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/reshape/merge.py:825(_reindex_and_concat)
      141    0.184    0.001    0.254    0.002 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/internals/blocks.py:816(copy)
        4    0.000    0.000    0.229    0.057 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/internals/managers.py:642(reindex_indexer)
        8    0.000    0.000    0.210    0.026 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/internals/managers.py:317(apply)
        6    0.000    0.000    0.209    0.035 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/internals/managers.py:576(copy)
   166/68    0.000    0.000    0.181    0.003 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/array_algos/take.py:59(take_nd)
        3    0.000    0.000    0.180    0.060 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/internals/managers.py:706(<listcomp>)
       64    0.000    0.000    0.179    0.003 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/internals/blocks.py:1353(take_nd)
      101    0.000    0.000    0.165    0.002 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/algorithms.py:1131(take)
        1    0.000    0.000    0.165    0.165 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/reshape/merge.py:1130(_get_join_info)
        1    0.002    0.002    0.165    0.165 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/reshape/merge.py:1120(_get_join_indexers)
        1    0.000    0.000    0.162    0.162 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/reshape/merge.py:1693(get_join_indexers)
      106    0.100    0.001    0.157    0.001 /Users/fqxin/Desktop/1019_Py/.venv/lib/python3.10/site-packages/pandas/core/array_algos/take.py:120(_take_nd_ndarray)
```
