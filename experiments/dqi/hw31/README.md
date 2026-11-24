# HW31 双载荷变换

`frame.json` 固定公开 f6b555a 电路的域词次序和两张 17×17 矩阵。左窗在两条载荷上施加 `output_matrix · Bez(f,g)⁻¹ · input_matrix`，右窗为其逆。系数和域词按低阶在前排列，域模为 `0x1053`。

`companion.py` 保留 17 阶互素输入的有限域求解和反向变换，包含零支点补阶。`euclid.py`、`multiply.py`、`tower_inverse.py` 和 `rank64.py` 提供可复用的域乘、倒数与系数运算。 [固定公开电路](https://www.kaggle.com/code/arsen123/qcc-28-24094-public-frontier-verified/versions/1)
