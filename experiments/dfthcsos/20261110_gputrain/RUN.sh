#!/bin/bash
# GPU training jobs for R5/R4 (JAX float64, needs: jax[cuda] optax numpy scipy h5py).
# Bundle layout mirrors repo: run from bundle root.
# Job A (primary): R5/B135/C70 from 2000-step checkpoint (85.31 mHa) -> 10000 total.
uv run --no-project --with "jax[cuda]" --with optax --with numpy --with scipy --with h5py \
  python experiments/dfthcsos/20261106_train_r5/fit_probe.py \
  artifacts/20261109_longloss/train_r5_l2_500to2000.npz \
  artifacts/20261110_gputrain/train_r5_l2_10000.npz --iters 8000 --chunk 100
# Job B: R4/B131/C83 from 180.11 mHa (500-step) -> 5000 total.
uv run --no-project --with "jax[cuda]" --with optax --with numpy --with scipy --with h5py \
  python experiments/dfthcsos/20261106_train_r5/fit_probe.py \
  artifacts/20261109_ubasis_retrain/train_r4_eigrr_500.npz \
  artifacts/20261110_gputrain/train_r4_eigrr_5000.npz --iters 4500 --chunk 100
