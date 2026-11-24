"""Accumulate a bilinear product using parity forms."""

import kickmix as km

from .euclid import indices


def rank_update(builder,x,y,z,terms):
    for a,b,c in terms:
        ax = [x[i] for i in indices(a)]
        by = [y[i] for i in indices(b)]
        cz = [z[i] for i in indices(c)]
        first = ax[1:] + by[1:] + [cz[0]] * (len(cz)-1)
        second = [ax[0]]*(len(ax)-1) + [by[0]]*(len(by)-1) + cz[1:]
        if first:
            builder.cx(km.array(first),km.array(second))
        builder.ccx(ax[0],by[0],cz[0])
        if first:
            builder.cx(km.array(first[::-1]),km.array(second[::-1]))
