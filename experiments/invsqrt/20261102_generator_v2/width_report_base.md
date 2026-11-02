# width_report.md：gen2 寿命实测（静态）

- 电路 qubits=160，文本行 94617，tracker max_allocated=123。
- 全局 first-last 峰值 160 @line 43177（阶段 F_S6），构成 {'x': 22, 'temp': 45, 'lz': 5, 'v': 55, 'coef': 33}。
- first-last 为静态近似（qubit 索引复用会合并 free 间隙，高估）；宽度真值以 alloc tracker 与 circuit.num_qubits 为准。
- 本电路为 width_opt62 加 STAGE 标记版（INFO_TAG 只增指令数，不占线、不改语义；SHA 与基线不同，见下）。
- instrumented SHA=98e3b5dadbdb0d6841334b82263354257206c60b46cdefd94746c88d2af6195d，基线 REC_SHA=4fe00ee7…（差值来自 INFO_TAG 标记行，门数差见 ops）。

## 阶段表（含 STAGE 标记区间行数 / distinct qubits / toffoli-like=CCX+CSWAP）

| 阶段 | 行区间 | 行数 | distinctQ | toff | 主要 ops |
|---|---|---|---|---|---|
| F_S1 | 23..7625 | 7603 | 51 | 922 | X:2062,CCX:922,R:882,HMR:882 |
| F_S2 | 7626..7698 | 73 | 27 | 61 | CSWAP:61,CX:8 |
| F_D | 7699..7824 | 126 | 27 | 12 | X:31,R:13,CX:13,HMR:13 |
| F_B | 7825..14344 | 6520 | 57 | 254 | CX:4474,X:511,R:255,HMR:255 |
| F_A_LOAD | 14345..19309 | 4965 | 46 | 254 | CX:2919,X:511,R:255,HMR:255 |
| F_A1 | 19310..25178 | 5869 | 124 | 1253 | CX:2604,CCX:1253,X:988,R:322 |
| A1_J0 | 19311..19792 | 482 | 112 | 109 | CX:212,CCX:109,X:88,R:23 |
| A1_J1 | 19793..20265 | 473 | 110 | 106 | CX:208,CCX:106,X:86,R:23 |
| A1_J2 | 20266..20729 | 464 | 108 | 103 | CX:204,CCX:103,X:84,R:23 |
| A1_J3 | 20730..21184 | 455 | 106 | 100 | CX:200,CCX:100,X:82,R:23 |
| A1_J4 | 21185..21630 | 446 | 104 | 97 | CX:196,CCX:97,X:80,R:23 |
| A1_J5 | 21631..22067 | 437 | 102 | 94 | CX:192,CCX:94,X:78,R:23 |
| A1_J6 | 22068..22495 | 428 | 100 | 91 | CX:188,CCX:91,X:76,R:23 |
| A1_J7 | 22496..22914 | 419 | 98 | 88 | CX:184,CCX:88,X:74,R:23 |
| A1_J8 | 22915..23324 | 410 | 96 | 85 | CX:180,CCX:85,X:72,R:23 |
| A1_J9 | 23325..23725 | 401 | 94 | 82 | CX:176,CCX:82,X:70,R:23 |
| A1_J10 | 23726..24117 | 392 | 92 | 79 | CX:172,CCX:79,X:68,R:23 |
| A1_J11 | 24118..24500 | 383 | 90 | 76 | CX:168,CCX:76,X:66,R:23 |
| A1_J12 | 24501..24874 | 374 | 88 | 73 | CX:164,CCX:73,X:64,R:23 |
| A1_J13 | 24875..25177 | 303 | 86 | 70 | CX:160,CCX:70,R:23,HMR:23 |
| F_A_UNLOAD | 25179..30143 | 4965 | 46 | 254 | CX:2919,X:511,R:255,HMR:255 |
| F_S3P | 30144..31567 | 1424 | 55 | 302 | CX:634,CCX:302,R:116,HMR:116 |
| F_R_LOAD | 31568..35227 | 3660 | 36 | 254 | CX:1614,X:511,R:255,HMR:255 |
| F_R1 | 35228..39339 | 4112 | 120 | 1206 | CX:2208,CCX:1206,R:216,HMR:216 |
| R1_J0 | 35229..35609 | 381 | 109 | 117 | CX:206,CCX:117,R:18,HMR:18 |
| R1_J1 | 35610..35983 | 374 | 107 | 114 | CX:202,CCX:114,R:18,HMR:18 |
| R1_J2 | 35984..36350 | 367 | 105 | 111 | CX:198,CCX:111,R:18,HMR:18 |
| R1_J3 | 36351..36710 | 360 | 103 | 108 | CX:194,CCX:108,R:18,HMR:18 |
| R1_J4 | 36711..37063 | 353 | 101 | 105 | CX:190,CCX:105,R:18,HMR:18 |
| R1_J5 | 37064..37409 | 346 | 99 | 102 | CX:186,CCX:102,R:18,HMR:18 |
| R1_J6 | 37410..37748 | 339 | 97 | 99 | CX:182,CCX:99,R:18,HMR:18 |
| R1_J7 | 37749..38080 | 332 | 95 | 96 | CX:178,CCX:96,R:18,HMR:18 |
| R1_J8 | 38081..38405 | 325 | 93 | 93 | CX:174,CCX:93,R:18,HMR:18 |
| R1_J9 | 38406..38723 | 318 | 91 | 90 | CX:170,CCX:90,R:18,HMR:18 |
| R1_J10 | 38724..39034 | 311 | 89 | 87 | CX:166,CCX:87,R:18,HMR:18 |
| R1_J11 | 39035..39338 | 304 | 87 | 84 | CX:162,CCX:84,R:18,HMR:18 |
| F_R_UNLOAD | 39340..42999 | 3660 | 36 | 254 | CX:1614,X:511,R:255,HMR:255 |
| F_S6 | 43000..43625 | 626 | 100 | 214 | CSWAP:162,CX:92,CCX:52,R:48 |
| R_S6 | 43626..44293 | 668 | 100 | 214 | CSWAP:162,X:110,CX:92,CCX:52 |
| R_R_LOAD | 44294..47953 | 3660 | 36 | 254 | CX:1614,X:511,R:255,HMR:255 |
| R_R1 | 47954..53013 | 5060 | 120 | 1206 | CX:2208,CCX:1206,X:948,R:216 |
| R1R_J11 | 47955..48326 | 372 | 87 | 84 | CX:162,CCX:84,X:68,R:18 |
| R1R_J10 | 48327..48707 | 381 | 89 | 87 | CX:166,CCX:87,X:70,R:18 |
| R1R_J9 | 48708..49097 | 390 | 91 | 90 | CX:170,CCX:90,X:72,R:18 |
| R1R_J8 | 49098..49496 | 399 | 93 | 93 | CX:174,CCX:93,X:74,R:18 |
| R1R_J7 | 49497..49904 | 408 | 95 | 96 | CX:178,CCX:96,X:76,R:18 |
| R1R_J6 | 49905..50321 | 417 | 97 | 99 | CX:182,CCX:99,X:78,R:18 |
| R1R_J5 | 50322..50747 | 426 | 99 | 102 | CX:186,CCX:102,X:80,R:18 |
| R1R_J4 | 50748..51182 | 435 | 101 | 105 | CX:190,CCX:105,X:82,R:18 |
| R1R_J3 | 51183..51626 | 444 | 103 | 108 | CX:194,CCX:108,X:84,R:18 |
| R1R_J2 | 51627..52079 | 453 | 105 | 111 | CX:198,CCX:111,X:86,R:18 |
| R1R_J1 | 52080..52541 | 462 | 107 | 114 | CX:202,CCX:114,X:88,R:18 |
| R1R_J0 | 52542..53012 | 471 | 109 | 117 | CX:206,CCX:117,X:90,R:18 |
| R_R_UNLOAD | 53014..56673 | 3660 | 36 | 254 | CX:1614,X:511,R:255,HMR:255 |
| R_S3P | 56674..58331 | 1658 | 55 | 302 | CX:634,CCX:302,X:278,R:116 |
| R_A_LOAD | 58332..63296 | 4965 | 46 | 254 | CX:2919,X:511,R:255,HMR:255 |
| R_A1 | 63297..68239 | 4943 | 124 | 1253 | CX:2604,CCX:1253,R:322,HMR:322 |
| A1R_J13 | 63298..63662 | 365 | 86 | 70 | CX:160,CCX:70,X:62,R:23 |
| A1R_J12 | 63663..63972 | 310 | 88 | 73 | CX:164,CCX:73,R:23,HMR:23 |
| A1R_J11 | 63973..64289 | 317 | 90 | 76 | CX:168,CCX:76,R:23,HMR:23 |
| A1R_J10 | 64290..64613 | 324 | 92 | 79 | CX:172,CCX:79,R:23,HMR:23 |
| A1R_J9 | 64614..64944 | 331 | 94 | 82 | CX:176,CCX:82,R:23,HMR:23 |
| A1R_J8 | 64945..65282 | 338 | 96 | 85 | CX:180,CCX:85,R:23,HMR:23 |
| A1R_J7 | 65283..65627 | 345 | 98 | 88 | CX:184,CCX:88,R:23,HMR:23 |
| A1R_J6 | 65628..65979 | 352 | 100 | 91 | CX:188,CCX:91,R:23,HMR:23 |
| A1R_J5 | 65980..66338 | 359 | 102 | 94 | CX:192,CCX:94,R:23,HMR:23 |
| A1R_J4 | 66339..66704 | 366 | 104 | 97 | CX:196,CCX:97,R:23,HMR:23 |
| A1R_J3 | 66705..67077 | 373 | 106 | 100 | CX:200,CCX:100,R:23,HMR:23 |
| A1R_J2 | 67078..67457 | 380 | 108 | 103 | CX:204,CCX:103,R:23,HMR:23 |
| A1R_J1 | 67458..67844 | 387 | 110 | 106 | CX:208,CCX:106,R:23,HMR:23 |
| A1R_J0 | 67845..68238 | 394 | 112 | 109 | CX:212,CCX:109,R:23,HMR:23 |
| R_A_UNLOAD | 68240..73204 | 4965 | 46 | 254 | CX:2919,X:511,R:255,HMR:255 |
| R_B | 73205..79724 | 6520 | 57 | 254 | CX:4474,X:511,R:255,HMR:255 |
| R_D | 79725..79820 | 96 | 26 | 12 | R:13,CX:13,HMR:13,CCX:12 |
| R_S2 | 79821..79893 | 73 | 27 | 61 | CSWAP:61,CX:8 |
| R_S1 | 79894..94616 | 14723 | 51 | 1762 | X:4022,CCX:1762,R:1722,HMR:1722 |

## alloc tracker（每 STAGE 标记点 num_allocated_qubits）

| 标记 | allocated |
|---|---|
| F_S1_ENTER | 115 |
| F_S1_EXIT | 115 |
| F_S2_ENTER | 115 |
| F_S2_EXIT | 115 |
| F_D_ENTER | 115 |
| F_D_EXIT | 115 |
| F_B_ENTER | 115 |
| F_B_EXIT | 115 |
| F_A_LOAD_ENTER | 115 |
| F_A_LOAD_EXIT | 115 |
| F_A1_ENTER | 115 |
| A1_J0_ENTER | 115 |
| A1_J0_EXIT | 115 |
| A1_J1_ENTER | 115 |
| A1_J1_EXIT | 115 |
| A1_J2_ENTER | 115 |
| A1_J2_EXIT | 115 |
| A1_J3_ENTER | 115 |
| A1_J3_EXIT | 115 |
| A1_J4_ENTER | 115 |
| A1_J4_EXIT | 115 |
| A1_J5_ENTER | 115 |
| A1_J5_EXIT | 115 |
| A1_J6_ENTER | 115 |
| A1_J6_EXIT | 115 |
| A1_J7_ENTER | 115 |
| A1_J7_EXIT | 115 |
| A1_J8_ENTER | 115 |
| A1_J8_EXIT | 115 |
| A1_J9_ENTER | 115 |
| A1_J9_EXIT | 115 |
| A1_J10_ENTER | 115 |
| A1_J10_EXIT | 115 |
| A1_J11_ENTER | 115 |
| A1_J11_EXIT | 115 |
| A1_J12_ENTER | 115 |
| A1_J12_EXIT | 115 |
| A1_J13_ENTER | 115 |
| A1_J13_EXIT | 115 |
| F_A1_EXIT | 115 |
| F_A_UNLOAD_ENTER | 115 |
| F_A_UNLOAD_EXIT | 115 |
| F_S3P_ENTER | 115 |
| F_S3P_EXIT | 115 |
| F_R_LOAD_ENTER | 115 |
| F_R_LOAD_EXIT | 115 |
| F_R1_ENTER | 115 |
| R1_J0_ENTER | 115 |
| R1_J0_EXIT | 115 |
| R1_J1_ENTER | 115 |
| R1_J1_EXIT | 115 |
| R1_J2_ENTER | 115 |
| R1_J2_EXIT | 115 |
| R1_J3_ENTER | 115 |
| R1_J3_EXIT | 115 |
| R1_J4_ENTER | 115 |
| R1_J4_EXIT | 115 |
| R1_J5_ENTER | 115 |
| R1_J5_EXIT | 115 |
| R1_J6_ENTER | 115 |
| R1_J6_EXIT | 115 |
| R1_J7_ENTER | 115 |
| R1_J7_EXIT | 115 |
| R1_J8_ENTER | 115 |
| R1_J8_EXIT | 115 |
| R1_J9_ENTER | 115 |
| R1_J9_EXIT | 115 |
| R1_J10_ENTER | 115 |
| R1_J10_EXIT | 115 |
| R1_J11_ENTER | 115 |
| R1_J11_EXIT | 115 |
| F_R1_EXIT | 115 |
| F_R_UNLOAD_ENTER | 115 |
| F_R_UNLOAD_EXIT | 115 |
| F_S6_ENTER | 115 |
| F_S6_EXIT | 115 |
| R_S6_ENTER | 115 |
| R_S6_EXIT | 115 |
| R_R_LOAD_ENTER | 115 |
| R_R_LOAD_EXIT | 115 |
| R_R1_ENTER | 115 |
| R1R_J11_ENTER | 115 |
| R1R_J11_EXIT | 115 |
| R1R_J10_ENTER | 115 |
| R1R_J10_EXIT | 115 |
| R1R_J9_ENTER | 115 |
| R1R_J9_EXIT | 115 |
| R1R_J8_ENTER | 115 |
| R1R_J8_EXIT | 115 |
| R1R_J7_ENTER | 115 |
| R1R_J7_EXIT | 115 |
| R1R_J6_ENTER | 115 |
| R1R_J6_EXIT | 115 |
| R1R_J5_ENTER | 115 |
| R1R_J5_EXIT | 115 |
| R1R_J4_ENTER | 115 |
| R1R_J4_EXIT | 115 |
| R1R_J3_ENTER | 115 |
| R1R_J3_EXIT | 115 |
| R1R_J2_ENTER | 115 |
| R1R_J2_EXIT | 115 |
| R1R_J1_ENTER | 115 |
| R1R_J1_EXIT | 115 |
| R1R_J0_ENTER | 115 |
| R1R_J0_EXIT | 115 |
| R_R1_EXIT | 115 |
| R_R_UNLOAD_ENTER | 115 |
| R_R_UNLOAD_EXIT | 115 |
| R_S3P_ENTER | 115 |
| R_S3P_EXIT | 115 |
| R_A_LOAD_ENTER | 115 |
| R_A_LOAD_EXIT | 115 |
| R_A1_ENTER | 115 |
| A1R_J13_ENTER | 115 |
| A1R_J13_EXIT | 115 |
| A1R_J12_ENTER | 115 |
| A1R_J12_EXIT | 115 |
| A1R_J11_ENTER | 115 |
| A1R_J11_EXIT | 115 |
| A1R_J10_ENTER | 115 |
| A1R_J10_EXIT | 115 |
| A1R_J9_ENTER | 115 |
| A1R_J9_EXIT | 115 |
| A1R_J8_ENTER | 115 |
| A1R_J8_EXIT | 115 |
| A1R_J7_ENTER | 115 |
| A1R_J7_EXIT | 115 |
| A1R_J6_ENTER | 115 |
| A1R_J6_EXIT | 115 |
| A1R_J5_ENTER | 115 |
| A1R_J5_EXIT | 115 |
| A1R_J4_ENTER | 115 |
| A1R_J4_EXIT | 115 |
| A1R_J3_ENTER | 115 |
| A1R_J3_EXIT | 115 |
| A1R_J2_ENTER | 115 |
| A1R_J2_EXIT | 115 |
| A1R_J1_ENTER | 115 |
| A1R_J1_EXIT | 115 |
| A1R_J0_ENTER | 115 |
| A1R_J0_EXIT | 115 |
| R_A1_EXIT | 115 |
| R_A_UNLOAD_ENTER | 115 |
| R_A_UNLOAD_EXIT | 115 |
| R_B_ENTER | 115 |
| R_B_EXIT | 115 |
| R_D_ENTER | 115 |
| R_D_EXIT | 115 |
| R_S2_ENTER | 115 |
| R_S2_EXIT | 115 |
| R_S1_ENTER | 115 |
| R_S1_EXIT | 115 |

## 峰值构成（实测，以 first-last @peak 为准）

- peak_line 43177 落在 `F_S6`；live 构成 x/lz/coef/v/temp = [22, 5, 33, 55, 45]。
- 预期 `ripple暂存~45 + coef33 + V55 + x22 (+lz5)` = 160；以本实测为准，见阶段表 R1_J0 行。

### 修正（2026-11-02 实测后补）：真峰值在 R1_J0，不在 S6

- first-last @peak 落在 F_S6 是 qubit 索引复用的人工假象：R1 的 45 暂存索引在 S6 被复用为增量暂存，
  first-last 把两段合并为“全程 live”，误把 S6 标为峰值点。真值以 `circuit.num_qubits=160`
  + 孤立探针（`probe_width_tmp.py` 实测）为准：
  - `num_allocated_qubits` 在 iadd 前后恒为 115（基座 x22+lz5+coef33+v55），内部 ripple 暂存走
    builder 内部 workspace（`num_qubits` 涨到 160，`num_allocated` 不动；`probe_cnt_tmp.py` 实测），
    故 alloc tracker 全程 115、max 123（仅含 addr 8）是基座口径，不是全宽。
  - 孤立探针（量子 offset、controlled）：`iadd off17→tgt45 extra45 / tgt44 extra44 / …`；
    `isub off22→tgt44 extra44 / …`；`iadd off9→tgt17 extra17`；经典 `iadd(1)→tgt36 extra35`；
    `flip22 extra21`。暂存 = len(target)（controlled 量子 offset 与经典增量均成立）。
  - 真 live = 基座 115 + 行暂存：R1_J0 `V[0:45)` len45 → 160（全局峰值，正/逆各一处 R1_J0/R1R_J0）；
    A1_J0 `V[1:45)` len44 → 159（次峰）；S6 增量 len36 → 115+35=150；square 最大 len17 → 132；
    sweep 期 115+addr8+unary8=131；S1 期 ~51。余量 0。
- 阶段表 distinctQ 偏小的原因：只计本段触及的 qubit（R1 行不触 x/lz，故 distinct≈108，
  漏计未触及但仍 live 的 x22+lz5）；真 live = 115 + (distinct − 本段触及基座)。不再以 distinctQ 为宽。
- R1 各行 distinctQ 与 toff（定位最宽调用点）：
  - R1_J0: distinctQ=109 toff=117 lines=381
  - R1_J1: distinctQ=107 toff=114 lines=374
  - R1_J10: distinctQ=89 toff=87 lines=311
  - R1_J11: distinctQ=87 toff=84 lines=304
  - R1_J2: distinctQ=105 toff=111 lines=367
  - R1_J3: distinctQ=103 toff=108 lines=360
  - R1_J4: distinctQ=101 toff=105 lines=353
  - R1_J5: distinctQ=99 toff=102 lines=346
  - R1_J6: distinctQ=97 toff=99 lines=339
  - R1_J7: distinctQ=95 toff=96 lines=332
  - R1_J8: distinctQ=93 toff=93 lines=325
  - R1_J9: distinctQ=91 toff=90 lines=318
  - A1_J0: distinctQ=112 toff=109 lines=482
  - A1_J1: distinctQ=110 toff=106 lines=473
  - A1_J10: distinctQ=92 toff=79 lines=392
  - A1_J11: distinctQ=90 toff=76 lines=383
  - A1_J12: distinctQ=88 toff=73 lines=374
  - A1_J13: distinctQ=86 toff=70 lines=303
  - A1_J2: distinctQ=108 toff=103 lines=464
  - A1_J3: distinctQ=106 toff=100 lines=455
  - A1_J4: distinctQ=104 toff=97 lines=446
  - A1_J5: distinctQ=102 toff=94 lines=437
  - A1_J6: distinctQ=100 toff=91 lines=428
  - A1_J7: distinctQ=98 toff=88 lines=419
  - A1_J8: distinctQ=96 toff=85 lines=410
  - A1_J9: distinctQ=94 toff=82 lines=401

## 逆向各段恢复成本（toffoli-like，逆序段）

- R_S6: toff=214 lines=668 distinctQ=100
- R_R_LOAD: toff=254 lines=3660 distinctQ=36
- R_R1: toff=1206 lines=5060 distinctQ=120
- R_R_UNLOAD: toff=254 lines=3660 distinctQ=36
- R_S3P: toff=302 lines=1658 distinctQ=55
- R_A_LOAD: toff=254 lines=4965 distinctQ=46
- R_A1: toff=1253 lines=4943 distinctQ=124
- R_A_UNLOAD: toff=254 lines=4965 distinctQ=46
- R_B: toff=254 lines=6520 distinctQ=57
- R_D: toff=12 lines=96 distinctQ=26
- R_S2: toff=61 lines=73 distinctQ=27
- R_S1: toff=1762 lines=14723 distinctQ=51

