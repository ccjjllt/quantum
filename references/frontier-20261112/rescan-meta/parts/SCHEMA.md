# Catalogue schema and evidence

The ZIP root contains a manifest with SHA-256 checks for each family. Each JSONL line is one record. `invsqrt/sources.jsonl` and `dqi/dqi_sources.jsonl` identify public source KMBs by SHA-256, author, notebook URL/version and license. `invsqrt/modules.jsonl` holds contiguous operation spans with entry and exit cut IDs, static resources, live wires and classical-record dependencies. `invsqrt/source_edges.jsonl` lists exact same-source adjacency; `cross_source_joins.jsonl` lists 45 tested joins and their scoped local verdicts. `cuts.jsonl` describes cut positions and context.

`chemistry/chemistry_modules.jsonl` holds one `angle_k` loader per row, source path/SHA, slot, incoming and outgoing word-block SHA, layout and parameters, compatible table IDs and provenance. `chemistry_word_tables.jsonl` and `chemistry_factorizations.jsonl` describe complete candidate sources; `chemistry_accuracy.jsonl` holds recorded pair gates; `chemistry_best_control.jsonl` gives a recorded complete 15-loader passing control.

`dqi/dqi_modules.jsonl` contains historical tagged source spans with static and sampled counts. `dqi_source_edges.jsonl` gives exact same-source adjacency. DQI cross-source value/phase interfaces are not exported.

Evidence status meanings: `exact_source_continuity` is byte-contiguous within the same source; `known_table_chain` checks one chemistry pair only; `local_all_x_cut_pass` is a scoped local inverse-square-root check; `rejected_at_this_cut` fails the tested cut; `unknown_cross_source_join` has no certificate. None alone proves an assembled whole circuit.
