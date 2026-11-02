# width_report.md：gen2 寿命实测（静态）

- 电路 qubits=159，文本行 101223，tracker max_allocated=134。
- 全局 first-last 峰值 159 @line 46393（阶段 F_S6），构成 {'x': 22, 'temp': 44, 'lz': 5, 'v': 55, 'coef': 33}。
- first-last 为静态近似（qubit 索引复用会合并 free 间隙，高估）；宽度真值以 alloc tracker 与 circuit.num_qubits 为准。
- 本电路为 width_opt62 加 STAGE 标记版（INFO_TAG 只增指令数，不占线、不改语义；SHA 与基线不同，见下）。
- instrumented SHA=a0992bc03b93e432f56d45bb85c094814e095d2064554852d1ee680fd5a370d0，基线 REC_SHA=4fe00ee7…（差值来自 INFO_TAG 标记行，门数差见 ops）。

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
| F_R1 | 35228..42555 | 7328 | 108 | 1908 | CX:3534,CCX:1908,X:408,CZ:396 |
| R1_J0 | 35229..35877 | 649 | 97 | 170 | CX:322,CCX:170,X:34,CZ:33 |
| R1_J1 | 35878..36519 | 642 | 96 | 168 | CX:317,CCX:168,X:34,CZ:33 |
| R1_J2 | 36520..37154 | 635 | 95 | 166 | CX:312,CCX:166,X:34,CZ:33 |
| R1_J3 | 37155..37782 | 628 | 94 | 164 | CX:307,CCX:164,X:34,CZ:33 |
| R1_J4 | 37783..38403 | 621 | 93 | 162 | CX:302,CCX:162,X:34,CZ:33 |
| R1_J5 | 38404..39017 | 614 | 92 | 160 | CX:297,CCX:160,X:34,CZ:33 |
| R1_J6 | 39018..39624 | 607 | 91 | 158 | CX:292,CCX:158,X:34,CZ:33 |
| R1_J7 | 39625..40224 | 600 | 90 | 156 | CX:287,CCX:156,X:34,CZ:33 |
| R1_J8 | 40225..40817 | 593 | 89 | 154 | CX:282,CCX:154,X:34,CZ:33 |
| R1_J9 | 40818..41403 | 586 | 88 | 152 | CX:277,CCX:152,X:34,CZ:33 |
| R1_J10 | 41404..41982 | 579 | 87 | 150 | CX:272,CCX:150,X:34,CZ:33 |
| R1_J11 | 41983..42554 | 572 | 86 | 148 | CX:267,CCX:148,X:34,CZ:33 |
| F_R_UNLOAD | 42556..46215 | 3660 | 36 | 254 | CX:1614,X:511,R:255,HMR:255 |
| F_S6 | 46216..47131 | 916 | 84 | 251 | CSWAP:162,X:116,CX:93,CCX:89 |
| R_S6 | 47132..48091 | 960 | 84 | 251 | X:188,CSWAP:162,CX:93,CCX:89 |
| R_R_LOAD | 48092..51751 | 3660 | 36 | 254 | CX:1614,X:511,R:255,HMR:255 |
| R_R1 | 51752..59619 | 7868 | 108 | 1908 | CX:3534,CCX:1908,X:948,CZ:396 |
| R1R_J11 | 51753..52358 | 606 | 86 | 148 | CX:267,CCX:148,X:68,CZ:33 |
| R1R_J10 | 52359..52973 | 615 | 87 | 150 | CX:272,CCX:150,X:70,CZ:33 |
| R1R_J9 | 52974..53597 | 624 | 88 | 152 | CX:277,CCX:152,X:72,CZ:33 |
| R1R_J8 | 53598..54230 | 633 | 89 | 154 | CX:282,CCX:154,X:74,CZ:33 |
| R1R_J7 | 54231..54872 | 642 | 90 | 156 | CX:287,CCX:156,X:76,CZ:33 |
| R1R_J6 | 54873..55523 | 651 | 91 | 158 | CX:292,CCX:158,X:78,CZ:33 |
| R1R_J5 | 55524..56183 | 660 | 92 | 160 | CX:297,CCX:160,X:80,CZ:33 |
| R1R_J4 | 56184..56852 | 669 | 93 | 162 | CX:302,CCX:162,X:82,CZ:33 |
| R1R_J3 | 56853..57530 | 678 | 94 | 164 | CX:307,CCX:164,X:84,CZ:33 |
| R1R_J2 | 57531..58217 | 687 | 95 | 166 | CX:312,CCX:166,X:86,CZ:33 |
| R1R_J1 | 58218..58913 | 696 | 96 | 168 | CX:317,CCX:168,X:88,CZ:33 |
| R1R_J0 | 58914..59618 | 705 | 97 | 170 | CX:322,CCX:170,X:90,CZ:33 |
| R_R_UNLOAD | 59620..63279 | 3660 | 36 | 254 | CX:1614,X:511,R:255,HMR:255 |
| R_S3P | 63280..64937 | 1658 | 55 | 302 | CX:634,CCX:302,X:278,R:116 |
| R_A_LOAD | 64938..69902 | 4965 | 46 | 254 | CX:2919,X:511,R:255,HMR:255 |
| R_A1 | 69903..74845 | 4943 | 124 | 1253 | CX:2604,CCX:1253,R:322,HMR:322 |
| A1R_J13 | 69904..70268 | 365 | 86 | 70 | CX:160,CCX:70,X:62,R:23 |
| A1R_J12 | 70269..70578 | 310 | 88 | 73 | CX:164,CCX:73,R:23,HMR:23 |
| A1R_J11 | 70579..70895 | 317 | 90 | 76 | CX:168,CCX:76,R:23,HMR:23 |
| A1R_J10 | 70896..71219 | 324 | 92 | 79 | CX:172,CCX:79,R:23,HMR:23 |
| A1R_J9 | 71220..71550 | 331 | 94 | 82 | CX:176,CCX:82,R:23,HMR:23 |
| A1R_J8 | 71551..71888 | 338 | 96 | 85 | CX:180,CCX:85,R:23,HMR:23 |
| A1R_J7 | 71889..72233 | 345 | 98 | 88 | CX:184,CCX:88,R:23,HMR:23 |
| A1R_J6 | 72234..72585 | 352 | 100 | 91 | CX:188,CCX:91,R:23,HMR:23 |
| A1R_J5 | 72586..72944 | 359 | 102 | 94 | CX:192,CCX:94,R:23,HMR:23 |
| A1R_J4 | 72945..73310 | 366 | 104 | 97 | CX:196,CCX:97,R:23,HMR:23 |
| A1R_J3 | 73311..73683 | 373 | 106 | 100 | CX:200,CCX:100,R:23,HMR:23 |
| A1R_J2 | 73684..74063 | 380 | 108 | 103 | CX:204,CCX:103,R:23,HMR:23 |
| A1R_J1 | 74064..74450 | 387 | 110 | 106 | CX:208,CCX:106,R:23,HMR:23 |
| A1R_J0 | 74451..74844 | 394 | 112 | 109 | CX:212,CCX:109,R:23,HMR:23 |
| R_A_UNLOAD | 74846..79810 | 4965 | 46 | 254 | CX:2919,X:511,R:255,HMR:255 |
| R_B | 79811..86330 | 6520 | 57 | 254 | CX:4474,X:511,R:255,HMR:255 |
| R_D | 86331..86426 | 96 | 26 | 12 | R:13,CX:13,HMR:13,CCX:12 |
| R_S2 | 86427..86499 | 73 | 27 | 61 | CSWAP:61,CX:8 |
| R_S1 | 86500..101222 | 14723 | 51 | 1762 | X:4022,CCX:1762,R:1722,HMR:1722 |

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

- peak_line 46393 落在 `F_S6`；live 构成 x/lz/coef/v/temp = [22, 5, 33, 55, 44]。
- 预期 `ripple暂存~45 + coef33 + V55 + x22 (+lz5)` = 160；以本实测为准，见阶段表 R1_J0 行。
- R1 各行 distinctQ 与 toff（定位最宽调用点）：
  - R1_J0: distinctQ=97 toff=170 lines=649
  - R1_J1: distinctQ=96 toff=168 lines=642
  - R1_J10: distinctQ=87 toff=150 lines=579
  - R1_J11: distinctQ=86 toff=148 lines=572
  - R1_J2: distinctQ=95 toff=166 lines=635
  - R1_J3: distinctQ=94 toff=164 lines=628
  - R1_J4: distinctQ=93 toff=162 lines=621
  - R1_J5: distinctQ=92 toff=160 lines=614
  - R1_J6: distinctQ=91 toff=158 lines=607
  - R1_J7: distinctQ=90 toff=156 lines=600
  - R1_J8: distinctQ=89 toff=154 lines=593
  - R1_J9: distinctQ=88 toff=152 lines=586
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

- R_S6: toff=251 lines=960 distinctQ=84
- R_R_LOAD: toff=254 lines=3660 distinctQ=36
- R_R1: toff=1908 lines=7868 distinctQ=108
- R_R_UNLOAD: toff=254 lines=3660 distinctQ=36
- R_S3P: toff=302 lines=1658 distinctQ=55
- R_A_LOAD: toff=254 lines=4965 distinctQ=46
- R_A1: toff=1253 lines=4943 distinctQ=124
- R_A_UNLOAD: toff=254 lines=4965 distinctQ=46
- R_B: toff=254 lines=6520 distinctQ=57
- R_D: toff=12 lines=96 distinctQ=26
- R_S2: toff=61 lines=73 distinctQ=27
- R_S1: toff=1762 lines=14723 distinctQ=51

