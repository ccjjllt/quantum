    # ---------------- angle retune by coordinate scan (robust; no LP conditioning issues)
    # The phase is exactly linear in the angles, so the error at every x after scaling
    # angle j by lam_j is  err_c + sum_j (lam_j - 1) * w_j * b_j(x).  We scan the 8
    # softest angles (the only ones that can move by a meaningful fraction) on a
    # multiplicative grid and keep the best max-ratio.  Also: drop-one / drop-two tests.
    try:
        fi = np.flatnonzero(fine)
        wf_u = w_all_u[fi]
        soft = np.argsort(wf_u)[:8]           # indices into fi, smallest angle first
        tol_f = tol_u.astype(np.float64)
        cols = [B[fi[k]].astype(np.float64) * wf_u[k] for k in range(len(fi))]

        def scan(free, max_sweeps=4, grid=np.linspace(0.5, 1.5, 41)):
            lam = np.ones(len(free))
            best_ratio = None
            for _ in range(max_sweeps):
                improved = False
                for a in range(len(free)):
                    k = free[a]
                    base = err_c.copy()
                    for b in range(len(free)):
                        if b != a:
                            base += (lam[b] - 1.0) * cols[free[b]]
                    cur_best = lam[a]
                    cur_ratio = None
                    for g in grid:
                        e = base + (g - 1.0) * cols[k]
                        r = float((np.abs(e) / tol_f).max())
                        if cur_ratio is None or r < cur_ratio:
                            cur_ratio, cur_best = r, g
                    if cur_ratio is not None and (best_ratio is None or cur_ratio < best_ratio - 1e-12):
                        best_ratio = cur_ratio
                        improved = True
                    lam[a] = cur_best
                if not improved:
                    break
            e = err_c.copy()
            for b in range(len(free)):
                e += (lam[b] - 1.0) * cols[free[b]]
            ratio = np.abs(e) / tol_f
            m_u = int(math.floor((tol_f - np.abs(e)).min()))
            return {"ratio_max": float(ratio.max()), "margin_units": m_u,
                    "lambdas": [float(x) for x in lam],
                    "angles_half_turns": [float(2.0 * wf_u[free[b]] * lam[b] / U)
                                          for b in range(len(free))]}

        shipped = {"ratio_max": float((used.astype(np.float64) / tol_f).max()),
                   "margin_units": margin_u}
        tuned = scan(list(soft))
        tuned["rot"] = rot_stats(tuned["margin_units"], len(fi))
        tuned["score"] = score_of(1454.000786597537, 2.4985437785547697,
                                  tuned["rot"]["t_total"] or 0.0)
        out["retune"] = {"shipped": shipped, "tuned_8_softest": tuned,
                         "free_fine_indices": [int(fi[k]) for k in soft],
                         "free_op_indices": [int(rots[fi[k]][2]) for k in soft],
                         "grid": [0.5, 1.5, 41]}
        print("RETUNE", json.dumps({k: v for k, v in tuned.items() if k != "lambdas"}), flush=True)

        drops = []
        for k in soft[:6]:
            free = [x for x in soft if x != k]
            base = err_c - cols[k]           # angle k removed entirely
            lam = np.ones(len(free))
            # same coordinate scan but on the reduced set
            for _ in range(4):
                for a in range(len(free)):
                    kk = free[a]
                    b0 = base.copy()
                    for b in range(len(free)):
                        if b != a:
                            b0 += (lam[b] - 1.0) * cols[free[b]]
                    cur_best, cur_ratio = lam[a], None
                    for g in np.linspace(0.5, 1.5, 41):
                        e = b0 + (g - 1.0) * cols[kk]
                        r = float((np.abs(e) / tol_f).max())
                        if cur_ratio is None or r < cur_ratio:
                            cur_ratio, cur_best = r, g
                    lam[a] = cur_best
            e = base.copy()
            for b in range(len(free)):
                e += (lam[b] - 1.0) * cols[free[b]]
            m2 = float((tol_f - np.abs(e)).min())
            drops.append({"drop_fine_index": int(fi[k]), "drop_op": int(rots[fi[k]][2]),
                          "angle_half_turns": float(2.0 * wf_u[k] / U),
                          "margin_units": int(math.floor(m2)),
                          "ratio_max": float((np.abs(e) / tol_f).max()),
                          "status": "ok" if m2 > 0 else "infeasible",
                          "rot": rot_stats(int(math.floor(m2)), len(fi) - 1)})
            print("drop", drops[-1], flush=True)
        out["drop_one"] = drops
        pairs = []
        if len(drops) >= 2:
            for a in range(min(3, len(drops))):
                for b in range(a + 1, min(3, len(drops))):
                    ks = [soft[a], soft[b]]
                    free = [x for x in soft if x not in ks]
                    base = err_c - cols[ks[0]] - cols[ks[1]]
                    lam = np.ones(len(free))
                    for _ in range(4):
                        for aa in range(len(free)):
                            kk = free[aa]
                            b0 = base.copy()
                            for bb in range(len(free)):
                                if bb != aa:
                                    b0 += (lam[bb] - 1.0) * cols[free[bb]]
                            cur_best, cur_ratio = lam[aa], None
                            for g in np.linspace(0.5, 1.5, 41):
                                e = b0 + (g - 1.0) * cols[kk]
                                r = float((np.abs(e) / tol_f).max())
                                if cur_ratio is None or r < cur_ratio:
                                    cur_ratio, cur_best = r, g
                            lam[aa] = cur_best
                    e = base.copy()
                    for bb in range(len(free)):
                        e += (lam[bb] - 1.0) * cols[free[bb]]
                    m2 = float((tol_f - np.abs(e)).min())
                    pairs.append({"drop_fine_indices": [int(fi[ks[0]]), int(fi[ks[1]])],
                                  "margin_units": int(math.floor(m2)),
                                  "status": "ok" if m2 > 0 else "infeasible"})
        out["drop_two"] = pairs
    except Exception as ex:
        out["retune_error"] = repr(ex)
        print("RETUNE ERROR", repr(ex), flush=True)
