# width_report.md：gen2 寿命实测（静态）

- 电路 qubits=149，文本行 124435，tracker max_allocated=134。
- 全局 first-last 峰值 149 @line 58131（阶段 F_S6），构成 {'x': 22, 'temp': 34, 'lz': 5, 'v': 55, 'coef': 33}。
- first-last 为静态近似（qubit 索引复用会合并 free 间隙，高估）；宽度真值以 alloc tracker 与 circuit.num_qubits 为准。
- 本电路为 width_opt62 加 STAGE 标记版（INFO_TAG 只增指令数，不占线、不改语义；SHA 与基线不同，见下）。
- instrumented SHA=4d43d989b9f9520fec11991b90f7bd511aa76a6df7bfd3a60822ed755bfe8efd，基线 REC_SHA=4fe00ee7…（差值来自 INFO_TAG 标记行，门数差见 ops）。

## 阶段表（含 STAGE 标记区间行数 / distinct qubits / toffoli-like=CCX+CSWAP）

| 阶段 | 行区间 | 行数 | distinctQ | toff | 主要 ops |
|---|---|---|---|---|---|
| F_S1 | 23..7625 | 7603 | 51 | 922 | X:2062,CCX:922,R:882,HMR:882 |
| F_S2 | 7626..7698 | 73 | 27 | 61 | CSWAP:61,CX:8 |
| F_D | 7699..7824 | 126 | 27 | 12 | X:31,R:13,CX:13,HMR:13 |
| F_B | 7825..14344 | 6520 | 57 | 254 | CX:4474,X:511,R:255,HMR:255 |
| F_A_LOAD | 14345..19309 | 4965 | 46 | 254 | CX:2919,X:511,R:255,HMR:255 |
| F_A1 | 19310..36916 | 17607 | 107 | 3982 | CX:6531,CCX:3982,X:2528,CZ:1260 |
| A1_J0 | 19311..20632 | 1322 | 94 | 299 | CX:499,CCX:299,X:198,CZ:90 |
| A1_J1 | 20633..21945 | 1313 | 92 | 297 | CX:494,CCX:297,X:196,CZ:90 |
| A1_J2 | 21946..23249 | 1304 | 90 | 295 | CX:489,CCX:295,X:194,CZ:90 |
| A1_J3 | 23250..24544 | 1295 | 89 | 293 | CX:484,CCX:293,X:192,CZ:90 |
| A1_J4 | 24545..25830 | 1286 | 88 | 291 | CX:479,CCX:291,X:190,CZ:90 |
| A1_J5 | 25831..27107 | 1277 | 87 | 289 | CX:474,CCX:289,X:188,CZ:90 |
| A1_J6 | 27108..28375 | 1268 | 86 | 287 | CX:469,CCX:287,X:186,CZ:90 |
| A1_J7 | 28376..29634 | 1259 | 85 | 285 | CX:464,CCX:285,X:184,CZ:90 |
| A1_J8 | 29635..30884 | 1250 | 84 | 283 | CX:459,CCX:283,X:182,CZ:90 |
| A1_J9 | 30885..32125 | 1241 | 83 | 281 | CX:454,CCX:281,X:180,CZ:90 |
| A1_J10 | 32126..33357 | 1232 | 82 | 279 | CX:449,CCX:279,X:178,CZ:90 |
| A1_J11 | 33358..34580 | 1223 | 81 | 277 | CX:444,CCX:277,X:176,CZ:90 |
| A1_J12 | 34581..35794 | 1214 | 80 | 275 | CX:439,CCX:275,X:174,CZ:90 |
| A1_J13 | 35795..36915 | 1121 | 79 | 251 | CX:434,CCX:251,X:110,CZ:90 |
| F_A_UNLOAD | 36917..41881 | 4965 | 46 | 254 | CX:2919,X:511,R:255,HMR:255 |
| F_S3P | 41882..43305 | 1424 | 55 | 302 | CX:634,CCX:302,R:116,HMR:116 |
| F_R_LOAD | 43306..46965 | 3660 | 36 | 254 | CX:1614,X:511,R:255,HMR:255 |
| F_R1 | 46966..54293 | 7328 | 108 | 1908 | CX:3534,CCX:1908,X:408,CZ:396 |
| R1_J0 | 46967..47615 | 649 | 97 | 170 | CX:322,CCX:170,X:34,CZ:33 |
| R1_J1 | 47616..48257 | 642 | 96 | 168 | CX:317,CCX:168,X:34,CZ:33 |
| R1_J2 | 48258..48892 | 635 | 95 | 166 | CX:312,CCX:166,X:34,CZ:33 |
| R1_J3 | 48893..49520 | 628 | 94 | 164 | CX:307,CCX:164,X:34,CZ:33 |
| R1_J4 | 49521..50141 | 621 | 93 | 162 | CX:302,CCX:162,X:34,CZ:33 |
| R1_J5 | 50142..50755 | 614 | 92 | 160 | CX:297,CCX:160,X:34,CZ:33 |
| R1_J6 | 50756..51362 | 607 | 91 | 158 | CX:292,CCX:158,X:34,CZ:33 |
| R1_J7 | 51363..51962 | 600 | 90 | 156 | CX:287,CCX:156,X:34,CZ:33 |
| R1_J8 | 51963..52555 | 593 | 89 | 154 | CX:282,CCX:154,X:34,CZ:33 |
| R1_J9 | 52556..53141 | 586 | 88 | 152 | CX:277,CCX:152,X:34,CZ:33 |
| R1_J10 | 53142..53720 | 579 | 87 | 150 | CX:272,CCX:150,X:34,CZ:33 |
| R1_J11 | 53721..54292 | 572 | 86 | 148 | CX:267,CCX:148,X:34,CZ:33 |
| F_R_UNLOAD | 54294..57953 | 3660 | 36 | 254 | CX:1614,X:511,R:255,HMR:255 |
| F_S6 | 57954..58869 | 916 | 84 | 251 | CSWAP:162,X:116,CX:93,CCX:89 |
| R_S6 | 58870..59829 | 960 | 84 | 251 | X:188,CSWAP:162,CX:93,CCX:89 |
| R_R_LOAD | 59830..63489 | 3660 | 36 | 254 | CX:1614,X:511,R:255,HMR:255 |
| R_R1 | 63490..71357 | 7868 | 108 | 1908 | CX:3534,CCX:1908,X:948,CZ:396 |
| R1R_J11 | 63491..64096 | 606 | 86 | 148 | CX:267,CCX:148,X:68,CZ:33 |
| R1R_J10 | 64097..64711 | 615 | 87 | 150 | CX:272,CCX:150,X:70,CZ:33 |
| R1R_J9 | 64712..65335 | 624 | 88 | 152 | CX:277,CCX:152,X:72,CZ:33 |
| R1R_J8 | 65336..65968 | 633 | 89 | 154 | CX:282,CCX:154,X:74,CZ:33 |
| R1R_J7 | 65969..66610 | 642 | 90 | 156 | CX:287,CCX:156,X:76,CZ:33 |
| R1R_J6 | 66611..67261 | 651 | 91 | 158 | CX:292,CCX:158,X:78,CZ:33 |
| R1R_J5 | 67262..67921 | 660 | 92 | 160 | CX:297,CCX:160,X:80,CZ:33 |
| R1R_J4 | 67922..68590 | 669 | 93 | 162 | CX:302,CCX:162,X:82,CZ:33 |
| R1R_J3 | 68591..69268 | 678 | 94 | 164 | CX:307,CCX:164,X:84,CZ:33 |
| R1R_J2 | 69269..69955 | 687 | 95 | 166 | CX:312,CCX:166,X:86,CZ:33 |
| R1R_J1 | 69956..70651 | 696 | 96 | 168 | CX:317,CCX:168,X:88,CZ:33 |
| R1R_J0 | 70652..71356 | 705 | 97 | 170 | CX:322,CCX:170,X:90,CZ:33 |
| R_R_UNLOAD | 71358..75017 | 3660 | 36 | 254 | CX:1614,X:511,R:255,HMR:255 |
| R_S3P | 75018..76675 | 1658 | 55 | 302 | CX:634,CCX:302,X:278,R:116 |
| R_A_LOAD | 76676..81640 | 4965 | 46 | 254 | CX:2919,X:511,R:255,HMR:255 |
| R_A1 | 81641..98057 | 16417 | 107 | 3718 | CX:6531,CCX:3718,X:1602,CZ:1260 |
| A1R_J13 | 81642..82846 | 1205 | 79 | 273 | CX:434,CCX:273,X:172,CZ:90 |
| A1R_J12 | 82847..83974 | 1128 | 80 | 253 | CX:439,CCX:253,X:110,CZ:90 |
| A1R_J11 | 83975..85109 | 1135 | 81 | 255 | CX:444,CCX:255,X:110,CZ:90 |
| A1R_J10 | 85110..86251 | 1142 | 82 | 257 | CX:449,CCX:257,X:110,CZ:90 |
| A1R_J9 | 86252..87400 | 1149 | 83 | 259 | CX:454,CCX:259,X:110,CZ:90 |
| A1R_J8 | 87401..88556 | 1156 | 84 | 261 | CX:459,CCX:261,X:110,CZ:90 |
| A1R_J7 | 88557..89719 | 1163 | 85 | 263 | CX:464,CCX:263,X:110,CZ:90 |
| A1R_J6 | 89720..90889 | 1170 | 86 | 265 | CX:469,CCX:265,X:110,CZ:90 |
| A1R_J5 | 90890..92066 | 1177 | 87 | 267 | CX:474,CCX:267,X:110,CZ:90 |
| A1R_J4 | 92067..93250 | 1184 | 88 | 269 | CX:479,CCX:269,X:110,CZ:90 |
| A1R_J3 | 93251..94441 | 1191 | 89 | 271 | CX:484,CCX:271,X:110,CZ:90 |
| A1R_J2 | 94442..95639 | 1198 | 90 | 273 | CX:489,CCX:273,X:110,CZ:90 |
| A1R_J1 | 95640..96844 | 1205 | 92 | 275 | CX:494,CCX:275,X:110,CZ:90 |
| A1R_J0 | 96845..98056 | 1212 | 94 | 277 | CX:499,CCX:277,X:110,CZ:90 |
| R_A_UNLOAD | 98058..103022 | 4965 | 46 | 254 | CX:2919,X:511,R:255,HMR:255 |
| R_B | 103023..109542 | 6520 | 57 | 254 | CX:4474,X:511,R:255,HMR:255 |
| R_D | 109543..109638 | 96 | 26 | 12 | R:13,CX:13,HMR:13,CCX:12 |
| R_S2 | 109639..109711 | 73 | 27 | 61 | CSWAP:61,CX:8 |
| R_S1 | 109712..124434 | 14723 | 51 | 1762 | X:4022,CCX:1762,R:1722,HMR:1722 |

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

- peak_line 58131 落在 `F_S6`；live 构成 x/lz/coef/v/temp = [22, 5, 33, 55, 34]。
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
  - A1_J0: distinctQ=94 toff=299 lines=1322
  - A1_J1: distinctQ=92 toff=297 lines=1313
  - A1_J10: distinctQ=82 toff=279 lines=1232
  - A1_J11: distinctQ=81 toff=277 lines=1223
  - A1_J12: distinctQ=80 toff=275 lines=1214
  - A1_J13: distinctQ=79 toff=251 lines=1121
  - A1_J2: distinctQ=90 toff=295 lines=1304
  - A1_J3: distinctQ=89 toff=293 lines=1295
  - A1_J4: distinctQ=88 toff=291 lines=1286
  - A1_J5: distinctQ=87 toff=289 lines=1277
  - A1_J6: distinctQ=86 toff=287 lines=1268
  - A1_J7: distinctQ=85 toff=285 lines=1259
  - A1_J8: distinctQ=84 toff=283 lines=1250
  - A1_J9: distinctQ=83 toff=281 lines=1241

## 逆向各段恢复成本（toffoli-like，逆序段）

- R_S6: toff=251 lines=960 distinctQ=84
- R_R_LOAD: toff=254 lines=3660 distinctQ=36
- R_R1: toff=1908 lines=7868 distinctQ=108
- R_R_UNLOAD: toff=254 lines=3660 distinctQ=36
- R_S3P: toff=302 lines=1658 distinctQ=55
- R_A_LOAD: toff=254 lines=4965 distinctQ=46
- R_A1: toff=3718 lines=16417 distinctQ=107
- R_A_UNLOAD: toff=254 lines=4965 distinctQ=46
- R_B: toff=254 lines=6520 distinctQ=57
- R_D: toff=12 lines=96 distinctQ=26
- R_S2: toff=61 lines=73 distinctQ=27
- R_S1: toff=1762 lines=14723 distinctQ=51

