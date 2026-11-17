# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Separate legal-endpoint helpers into low truth tables and high ANF forms."""
import numpy as np


def separate(table):
    table=np.asarray(table,dtype=np.uint8)
    assert table.ndim==2 and table.shape[1]==5 and len(table)%16==0
    low=table[:16].copy()
    high=table[::16].copy()^low[0]
    addresses=np.arange(len(table))
    assert np.array_equal(table,low[addresses%16]^high[addresses//16]), \
        'Helper is not a sum of a low-only and a high-only function'
    anf=high.copy()
    for bit in range((len(high)-1).bit_length()):
        for h in range(len(high)):
            if h>>bit&1:anf[h]^=anf[h^(1<<bit)]
    assert not np.any(anf[0])
    return low,anf
