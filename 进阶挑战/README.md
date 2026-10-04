# 「五、进阶挑战」README 正文（可直接贴进仓库）

> **用法**：把下面「===== 粘贴开始 =====」到「===== 粘贴结束 =====」之间的内容整段复制进你的仓库 `README.md`。
> - 我按你现有 README 的编号习惯写成 **`## 七、进阶挑战`**（因为你的「五、关键提示词」「六、踩过的坑」已经被占用了）。
>   如果你更想放在「四、小游戏」后面，把标题改成 `## 进阶挑战：用 PySpice 验证三个电路（任务书第五项）` 即可，任务书只要求 README 里有这些内容，不要求编号。
> - 三个脚本就在这个目录里：`rc_lowpass.py`、`thevenin.py`、`mos_common_source.py`。
>   运行时请把这三个文件也复制到仓库的 `进阶挑战/` 目录下（任务书要求：**三个 .py 文件直接上传到仓库**）。
> - 下面所有「仿真值 / 误差」已经是**真实跑出来的数字**（PySpice 1.5 + ngspice-38 共享库模式，2026-10-03 实测），
>   你在自己电脑上跑同样三个脚本会得到几乎相同的值（表格里的数字可以直接用）。
> - 6 张手画电路图仍需你自己画（见文末「画图清单」）。

===== 粘贴开始 =====

## 七、进阶挑战：用 PySpice 验证三个电路

我选的是任务书第五项里的**第一项（三个电路）**：RC 滤波电路、验证戴维南定理、NMOS 共源放大电路。
三个电路都用 **PySpice 1.5 + ngspice（共享库 ngspice.dll）** 仿真（PySpice 是 ngspice 的 Python 封装，网表用 Python 代码描述），
代码在 `进阶挑战/` 目录：

| 文件 | 对应电路 | 输出的数据/图 |
| --- | --- | --- |
| `进阶挑战/rc_lowpass.py` | ① RC 低通滤波 | `figures/rc_transient.png`（瞬态波形）、`figures/rc_bode.png`（波特图）、`figures/rc_transient.csv`、`figures/rc_ac.csv` |
| `进阶挑战/thevenin.py` | ② 验证戴维南定理 | `figures/thevenin_load.png`（负载特性）、`figures/thevenin_load.csv` |
| `进阶挑战/mos_common_source.py` | ③ NMOS 共源放大电路 | `figures/mos_cs_transient.png`（输入/输出波形）、`figures/mos_cs_transient.csv` |

三个脚本都是**手算 + 仿真对照**：正文里先写手算公式和过程，再让脚本用 ngspice 跑出仿真值，最后打印误差表。

### 7.1 环境准备（Windows，我自己踩过的顺序）

1. 装 **Python**：打开 https://www.python.org/downloads/ 下载 Windows 64 位安装包（我装的是 3.13.x，
   追求最新也可以装首页的 3.14.x）。双击安装时**第一步一定要勾上 `Add python.exe to PATH`**，再点 Install Now。
   装完关掉所有终端、重新开一个 PowerShell 验证：
   ```powershell
   python --version            # 应打印 Python 3.13.x
   python -m pip --version     # 应打印 pip 版本
   ```
   如果 `python` 直接跳转微软商店：去「设置 → 应用 → 高级应用设置 → 应用执行别名」关掉 `python.exe` / `python3.exe` 的别名。
2. 装 Python 依赖（注意必须用 `python -m pip`，否则可能装到另一个 Python 里）：
   ```powershell
   python -m pip install -U pip
   python -m pip install PySpice numpy matplotlib cffi
   ```
   （`cffi` 看着像可选项，其实 PySpice 在 Windows 上**必须**有它才能 import。）
3. 准备 **ngspice**：Windows 上**不要**去 SourceForge 下 `ngspice-47_64.7z`（那个源在国内只有十几 KB/s，
   而且下下来的命令行版在 PySpice 里根本跑不通，原因见 7.6）。正确做法是拿 **conda-forge 的 ngspice 包**，
   里面带 `ngspice.dll`，PySpice 用「共享库模式」调用它。国内用上海交大镜像很快（实测 2.5 MB/s 以上）：
   ```powershell
   mkdir D:\ngspice\Spice64 -Force
   cd D:\ngspice
   curl.exe -L -o ngspice-lib.tar.bz2 "https://mirror.sjtu.edu.cn/anaconda/cloud/conda-forge/win-64/ngspice-lib-38-h295a5eb_0.tar.bz2"
   curl.exe -L -o ngspice-exe.tar.bz2 "https://mirror.sjtu.edu.cn/anaconda/cloud/conda-forge/win-64/ngspice-exe-38-h295a5eb_0.tar.bz2"
   python -c "import tarfile;[tarfile.open(f).extractall(r'D:\ngspice\Spice64') for f in ('ngspice-lib.tar.bz2','ngspice-exe.tar.bz2')]"
   ```
   解压完应该能看到 `D:\ngspice\Spice64\Library\bin\ngspice.dll`（这就是仿真内核）。
   （用 Python 自带的 tarfile 解压，所以**连 7-Zip 都不用装**；`ngspice-exe` 里的 `bin\ngspice.exe` 是 GUI 版，
   命令行下没有输出，本项目不用它。）
4. 让脚本找到 ngspice：把 ngspice 目录放在**脚本的上一级**（也就是 `进阶挑战\..\ngspice\Spice64\...`）就行，
   三个脚本开头的 `_find_ngspice()` 会自动搜索（也支持 `D:\ngspice`、`C:\ngspice` 等常见位置）。
   想手动指定也行：
   ```powershell
   $env:NGSPICE_LIBRARY_PATH="D:\ngspice\Spice64\Library\bin\ngspice.dll"
   $env:SPICE_LIB_DIR="D:\ngspice\Spice64\Library\share\ngspice"
   ```
   （这两个变量要**同时**设：PySpice 只拿到 dll 路径时，内部还会去拼 `Path(None)` 而抛 TypeError。）
5. 跑脚本：`python rc_lowpass.py`。看到 `[ngspice] 共享库模式，ngspice.dll = ...` 就说明连上了；
   如果打印「没找到 ngspice」，说明第 3 步的目录不在脚本的搜索路径里。

### 7.2 电路一：RC 低通滤波电路

**元件参数（自定）**：R = 1 kΩ，C = 100 nF；输入 1 kHz、0~1 V 方波；交流扫描 10 Hz ~ 100 kHz。

**电路图**（我自己画的，`figures/rc_circuit.jpg`）：R 与 C 串联，输入 `v_i` 加在 RC 串联支路两端，
输出 `v_o` 从电容 C 两端取，电容下端接地。

**理论值手算**

- 时间常数：τ = RC = 1×10³ Ω × 100×10⁻⁹ F = 1×10⁻⁴ s = **100 µs**
- 截止频率：f_c = 1/(2πRC) = 1/(2π×1×10⁻⁴) ≈ **1591.5 Hz**
- 传递函数：H(jω) = 1/(1+jωRC)，幅频 |H| = 1/√(1+(f/f_c)²)，相频 ∠H = −arctan(f/f_c)
  - f = f_c：|H| = 0.7071（−3.01 dB），相移 −45°
  - f = 10f_c：|H| = 1/√101 ≈ 0.0995（−20.05 dB）→ 一阶低通 −20 dB/十倍频
- 方波响应：半周期 T/2 = 500 µs = 5τ，每次充电都能充到接近稳态，所以输出是**指数充放电波形**（近似三角波）；
  阶跃响应 v_o(t) = V(1 − e^(−t/τ))，于是 t = τ 时到 0.632 V、t = 3τ 时到 0.950 V。

**仿真怎么设**：瞬态分析 1 µs 步长、3 ms（3 个周期），输入 `PULSE(0 1 0 1u 1u 0.5m 1m)`；
交流分析 10 Hz→100 kHz、10 点/十倍频，输入源自带 `AC 1`。

**① 时间常数与截止频率对比表**

| 项目 | 手算值 | 仿真值 | 误差 |
| --- | --- | --- | --- |
| τ = RC | 100.0 µs | 100.7 µs（由仿真波形的上升段按 τ = −t/ln(1−v_o/V_high) 反推） | 0.70 % |
| V_o 稳态（半周期 5τ 处） | 0.9933 V | 0.9932 V | 0.01 % |
| v_o 到达 0.95 V 的时刻 | 299.6 µs（= −τ·ln(1−0.95/1)） | 300.1 µs | 0.17 % |
| f_c（\|H\| 降到 0.7071 处） | 1591.55 Hz | 1591.48 Hz | 0.00 % |
| \|H\| @ f_c | 0.7071（−3.01 dB） | 0.7071 | 0.00 % |
| \|H\| @ 10f_c | 0.0995（−20.05 dB） | 0.0995 | — |

（上表就是脚本 `rc_lowpass.py` 打印的内容；`figures/rc_transient.csv`、`figures/rc_ac.csv` 是原始数据。）

**图**：图 1 手画电路图 `figures/rc_circuit.jpg`；图 2 方波输入/输出瞬态波形 `figures/rc_transient.png`；
图 3 波特图（幅频 + 相频）`figures/rc_bode.png`。

### 7.3 电路二：验证戴维南定理

**电路参数（自定）**：含源二端网络 = V1 = 12 V 串 R1 = 1 kΩ，V2 = 6 V 串 R2 = 2 kΩ，
两支路并联后经 R3 = 3 kΩ 回到公共端；端口 a–b 就是 R3 两端（开路端）。

**电路图**（我自己画的）：`figures/thevenin_network.jpg` 画原网络并**标出端口 a、b**；
`figures/thevenin_equivalent.jpg` 画等效电路（V_th 串联 R_th，再接负载 R_L）。

**理论值手算**（戴维南定理：任一含源线性二端网络可等效为「V_th 串联 R_th」，V_th = 端口开路电压，R_th = 内部独立源置零后的端口等效电阻）

- 端口开路电压（节点法，节点 a）：
  (V1 − V_oc)/R1 + (V2 − V_oc)/R2 = V_oc/R3
  ⇒ V_oc = (V1/R1 + V2/R2) / (1/R1 + 1/R2 + 1/R3)
  = (12/1000 + 6/2000) / (1/1000 + 1/2000 + 1/3000)
  = (15×10⁻³ A) / (1.8333×10⁻³ S) = **8.1818 V**
- 等效内阻（电压源短路）：R_th = R1∥R2∥R3 = 1/(1.8333×10⁻³) = **545.45 Ω**
- 短路电流：I_sc = V_th/R_th = 8.1818/545.45 = **15.000 mA**
- 接负载：V_L = V_th·R_L/(R_th+R_L)，I_L = V_L/R_L

**仿真怎么设**：跑三次——
① 开路：端口悬空，读 a 点电压 → V_oc；
② 短路：端口接一个 0 V 电压源（等于理想电流表），读该支路电流 → I_sc；
③ 负载验证：把负载接在原网络端口上，再把负载接在「V_th 串 R_th」的等效电路上，对比两者的 V_L / I_L。
另外做一次负载参数扫描（100 Ω ~ 10 kΩ），得到负载特性曲线 `figures/thevenin_load.png`。

**② 开路/短路两次仿真对比表**

| 量 | 手算值 | 仿真值 | 误差 |
| --- | --- | --- | --- |
| V_oc = V_th | 8.1818 V | 8.1818 V | 0.00 % |
| I_sc | 15.0000 mA | 15.0000 mA | 0.00 % |
| 由仿真反推 R_th = V_oc/I_sc | 545.45 Ω | 545.45 Ω | 0.00 % |

**③ 等效电路替换后接负载的验证表**

| 负载 R_L | 手算 V_L / I_L | 原网络仿真 | 等效电路仿真 | 误差 |
| --- | --- | --- | --- | --- |
| 1 kΩ | 5.2941 V / 5.2941 mA | 5.2941 V / 5.2941 mA | 5.2941 V / 5.2941 mA | 0.00 % |
| 470 Ω | 3.7869 V / 8.0573 mA | 3.7869 V / 8.0573 mA | 3.7869 V / 8.0573 mA | 0.00 % |
| 2.2 kΩ | 6.5563 V / 2.9801 mA | 6.5563 V / 2.9801 mA | 6.5563 V / 2.9801 mA | 0.00 % |

（额外结论：原网络与等效电路在同一负载下电压/电流完全一致，误差只来自数值精度 → 戴维南定理得到验证。）

### 7.4 电路三：NMOS 共源放大电路

**参数（按题卡固定）**：V_DD = 5 V，R_g1 = 60 kΩ，R_g2 = 40 kΩ，R_d = 2 kΩ，
NMOS：K = 0.8 mA/V²、V_th = 1 V、λ = 0.02 /V；输入 v_i = 10 mV / 1 kHz 正弦；
C_b1 视为足够大（仿真里取 10 µF）。

**电路图**（我自己画的，`figures/mos_circuit.jpg`）：V_DD 经 R_d 接漏极 d，输出 v_o 从 d 引出；
R_g1（60 kΩ）与 R_g2（40 kΩ）串联在 V_DD 与地之间，中点经 C_b1 接栅极 g 并接输入 v_i；
源极 s 接地（衬底 B 与 s 相连）。

**理论值手算（直流工作点）**

1. 直流通路里 C_b1 是**开路**，输入 v_i 不参与，栅极电流为 0，所以 R_g1、R_g2 就是纯分压：
   V_G = V_DD·R_g2/(R_g1+R_g2) = 5×40/(60+40) = **2.0 V**，源极接地 ⇒ **V_GS = 2.0 V**
2. 过驱动电压：V_ov = V_GS − V_th = 2.0 − 1 = **1.0 V**
3. 先忽略 λ：I_D = ½K·V_ov² = ½×0.8 mA/V²×(1 V)² = **0.4 mA**
   V_DS = V_DD − I_D·R_d = 5 − 0.4 mA×2 kΩ = **4.2 V**
4. 饱和区判据：V_DS > V_GS − V_th = 1.0 V → 4.2 V ≫ 1.0 V，**工作在饱和区（恒流区）**
5. 再把沟道长度调制 λ 算进去：I_D = ½K·V_ov²(1+λV_DS)，同时 V_DS = V_DD − I_D·R_d，
   记 a = ½K·V_ov² = 0.4 mA，解出
   **I_D = a(1+λV_DD)/(1 + aλR_d) = 0.4×(1+0.02×5)/(1+0.4×10⁻³×0.02×2000) = 0.4×1.1/1.016 = 0.4331 mA**
   **V_DS = 5 − 0.4331 mA×2 kΩ = 4.1339 V**（仍满足 V_DS > 1.0 V，自洽，饱和区）

**理论值手算（小信号参数与增益）**

- 跨导：g_m = ∂I_D/∂V_GS = K·V_ov·(1+λV_DS) = 0.8×10⁻³×1.0×(1+0.02×4.1339) = **0.8661 mS**
  （用 g_m = 2I_D/V_ov = 2×0.4331 mA/1 V = 0.8662 mS 交叉验证，两者一致）
- 输出电阻：r_o = 1/(λI_D) = 1/(0.02×0.4331×10⁻³) = **115.45 kΩ**
- 漏极等效负载：R_d∥r_o = 2000×115450/(2000+115450) = **1965.9 Ω**
- 电压增益：A_v = −g_m(R_d∥r_o) = −0.8661×10⁻³×1965.9 = **−1.7028 V/V（−4.62 dB，反相）**
- 输出幅值：10 mV×1.7028 ≈ **17.03 mV（与输入反相）**

**小信号等效模型**（`figures/mos_small_signal.jpg`）：栅极节点接 R_g = R_g1∥R_g2 = 24 kΩ 到地；
用 v_gs 控制一个 g_m·v_gs 的电流源（从漏极流向源极），它和 r_o 并联；R_d 接在漏极与地之间；
输出 v_o 取在漏极。因为源极接地、V_DD 是交流地，所以 R_g1/R_g2 在交流上也等效并联。

**仿真怎么设**：① 直流工作点 `op` 分析，读工作点（漏极电流用一个串联 0 V 电压源 V_sense 读，避免读错支路）；
② 瞬态分析 1 µs 步长、3 ms，输入 `SIN(0 10m 1k)`，看输出波形、量峰峰值算实测增益。

**④ 直流工作点对比表（含饱和区判断）**

| 量 | 手算值 | 仿真值 | 误差 |
| --- | --- | --- | --- |
| V_GS | 2.000 V | 2.0000 V | 0.00 % |
| I_D | 0.4331 mA | 0.4331 mA | 0.00 % |
| V_DS | 4.1339 V | 4.1339 V | 0.00 % |
| 工作区判断 | V_DS = 4.13 V > V_GS − V_th = 1.0 V，饱和区 | 仿真得到的 V_DS = 4.13 V 同样 > 1 V，饱和区 | — |

**⑤ 小信号参数与增益对比表（瞬态实测增益）**

| 量 | 手算值 | 仿真值 | 误差 |
| --- | --- | --- | --- |
| g_m | 0.8661 mS | 0.8661 mS（由仿真的 g_m = 2I_D/V_ov 反推） | 0.00 % |
| r_o | 115.45 kΩ | 115.45 kΩ（由仿真的 I_D 与 λ 反推） | 0.00 % |
| 输出幅值 | 17.028 mV | 17.050 mV（瞬态读数） | 0.13 % |
| 电压增益 \|A_v\| | 1.7028（4.62 dB） | 1.7050（4.63 dB）（输出峰峰值 ÷ 输入峰峰值） | 0.13 % |
| 输出直流电平 | 4.1339 V | 4.1338 V | 0.00 % |
| 相位关系 | 反相（−180°） | 实测反相（输出波谷对应输入波峰） | — |

**图**：图 6 手画电路图 `figures/mos_circuit.jpg`；图 7 直流通路 `figures/mos_dc_path.jpg`；
图 8 小信号等效模型 `figures/mos_small_signal.jpg`；图 9 输入/输出瞬态波形 `figures/mos_cs_transient.png`。

**为什么手算和仿真几乎完全一样**：ngspice 的 MOS Level-1 模型（KP / VTO / LAMBDA）用的就是上面那组公式，
所以只要 λ 和栅极分压没算错，两者误差通常 < 0.1%；如果误差很大，先检查是不是漏了 λ，或者读电流时读错了支路。

### 7.5 怎么运行 / 怎么验证

```powershell
cd 进阶挑战
python rc_lowpass.py          # ① RC：打印 τ、f_c 的对比表 + 写 figures/rc_*.png/csv
python thevenin.py            # ② 戴维南：打印 V_oc、I_sc、负载验证表 + 写 figures/thevenin_load.*
python mos_common_source.py   # ③ MOS：打印工作点、g_m、A_v 对比表 + 写 figures/mos_cs_transient.*
```

每个脚本都是「先手算、再仿真、最后打印误差表」，所以验证很直接：

1. **看误差列**：V_oc / I_sc / V_GS / I_D / V_DS / f_c 这些量的误差是 0.00%（同一套公式，只有数值精度差别）；
   τ 和瞬态增益的误差在 0.1%~0.7% 之间（受 1 µs 时间步长限制）。
2. **看原始数据**：`figures/*.csv` 用 Excel 打开画一下——RC 的 v_o 是指数充放电、MOS 的 v_o 是反相正弦（直流偏置 4.13 V）。
3. **看图和手算对上没**：RC 的 −3 dB 点在 1591 Hz 附近（波特图）；MOS 输出峰峰值 ≈ 34 mV（17 mV 幅值 ×2）；
   戴维南的负载特性曲线是一条从 8.18 V 往下走的直线（R_L 越小压降越大）。
4. **反编译验证**（可选，但很有说服力）：把 `rc_lowpass.py` 里的 R、C 改成别的值（比如 2 kΩ / 47 nF），
   手算 τ、f_c 再跑一遍，误差仍然在 1% 以内 → 说明不是“凑数”凑出来的。

### 7.6 这一步踩过的坑

**（1）Windows 上 ngspice 的「命令行模式」在 PySpice 里根本跑不通。**
这是最坑的一个。PySpice 默认用 `ngspice -s` 起一个服务器进程，然后把网表塞进它的 stdin、从 stdout 读回「raw 文件」。
实测（ngspice-38/47 都一样）有两处对不上：
- ngspice 自带的 `spinit` 里写着 `set filetype=ascii`，raw 文件输出成**纯文本**，而 PySpice 的解析器死找 `Binary:` 标记
  → 报 `NameError: Cannot locate binary data`；
- ngspice 启动后 stdout 开头会多一行 `Note: No compatibility mode selected!`，而 PySpice 要求输出**第一行**就是 `Circuit:`
  → 我用 `.spiceinit`、`SPICE_LIB_DIR` 换 spinit、往网表里注入 `.control set filetype=binary .endc` 试了一圈，
  要么修好第一条、要么修好第二条，**永远有一条挡着**。

真正的解法是改用**共享库模式**（`simulator='ngspice-shared'`，用 `ngspice.dll` 直接调用仿真内核）——
这也正是 PySpice 在 Windows 上的默认模式。所以三个脚本里都写了一段 `_find_ngspice()` 自动找 dll 并自动切模式。
（顺带：conda-forge 包里 `bin\ngspice.exe` 是 GUI 版，命令行下**完全不输出**，别拿它调 PATH 测试，要用 `ngspice_con.exe`。）

**（2）只设 `NGSPICE_LIBRARY_PATH` 还不够。** PySpice 的 `Shared.py` 里，如果没设 `SPICE_LIB_DIR`，
它会用 `Path(self.NGSPICE_PATH)` 去拼路径，而此时 `NGSPICE_PATH` 是 `None` → 直接抛 `TypeError`。两个变量要同时设。

**（3）网表里 MOS 的源极忘了接地，仿真结果离谱。** 我第一版写成 `M1 d g s s nmos1`（源极、衬底都接在节点 `s` 上），
但 `s` 没有连到地，直流上是个“只接晶体管端子”的悬空节点，ngspice 只能靠结漏电收敛 →
仿真给出 `V_GS = −3.01 V、I_D ≈ 0`，跟手算的 `2 V / 0.4331 mA` 差了十万八千里。改成源极接 0（地）后立刻变成 0.00% 误差。
**教训：误差很大时先查拓扑（尤其“悬空节点”），不要急着怀疑模型参数。**

**（4）读电压源支路电流时不能自己调用 `simulation.save()`。**
PySpice 只有在"没有 `.save` 指令"的情况下才让 ngspice 默认保存全部节点电压和电压源支路电流；
我为了读短路电流 `I_sc` 和漏极电流 `I_D`，特意串了 0 V 电压源当电流表，一旦手动 save 就读不到支路电流了。

**（5）模型名必须写关键字。** `c.M(1,'d','g','s','s','nmos1')` 会报 `NameError: Number of args mismatch`，
要写成 `c.M(1,'d','g','s','s', model='nmos1', w=1e-6, l=1e-6)`。

**（6）节点名不能叫 `in`**（Python 关键字），PySpice 会报警告，改叫 `vin` 就好。

**（7）时间常数不能拿两点一减就当 τ。** 我一开始用"0.5 V 穿越时刻到 0.632 V 穿越时刻之差"当 τ，
结果 32 µs（真实值 100 µs）——那两个点之间只差 0.307τ。正确做法是按指数公式反推：τ = −t/ln(1 − v_o/V_high)，
在上升段取一批采样点求平均，这样得到 100.7 µs。

**（8）中文 Windows 控制台打印 µ、Ω 会崩。** 重定向输出时 `print` 会抛
`UnicodeEncodeError: 'gbk' codec can't encode character '\xb5'`，脚本里加了 `sys.stdout.reconfigure(errors='replace')` 兜底。

**（9）两条无害的报错，别被吓到**：跑脚本时 stderr 会有 `Unsupported Ngspice version 38`
（PySpice 1.5 只认到 ngspice 34，新版落到"最后一种仿真类型"分支，只影响提示不影响结果），
以及 cffi 回调里的 `TypeError: a bytes-like object is required, not 'str'`（PySpice 在 Windows 上的已知小 bug）。

**（10）没装 matplotlib 不会崩**，脚本会跳过画图只存 CSV；但要交波形图还是得 `pip install matplotlib`。

===== 粘贴结束 =====

---

## 附：需要你自己动手的 6 张手画图（画图清单）

任务书要求“电路图自己画（手绘拍照/画图软件都可以）”，下面 6 张按这个清单画就行，画完存成同名文件放进 `进阶挑战/figures/`：

| 文件名 | 画什么 | 必须标出的东西 |
| --- | --- | --- |
| `rc_circuit.jpg` | R 与 C 串联，C 下端接地；输入 `v_i` 加在串联支路两端，输出 `v_o` 取自 C 两端 | v_i、v_o、R、C、接地符号 |
| `thevenin_network.jpg` | 原含源二端网络：V1 串 R1、V2 串 R2 两支路并联，经 R3 回公共端 | 端口 a、b（画成两个小圆圈端子）、V1/V2/R1/R2/R3 的数值 |
| `thevenin_equivalent.jpg` | 等效电路：V_th 串联 R_th，端口接负载 R_L | V_th=8.18 V、R_th=545.45 Ω、R_L、端口 a/b、V_L 与 I_L 的方向 |
| `mos_circuit.jpg` | 题卡那张 NMOS 共源放大电路 | V_DD=5 V、R_g1=60 kΩ、R_g2=40 kΩ、R_d=2 kΩ、C_b1、g/d/s/B、v_i、v_o、i_D 方向 |
| `mos_dc_path.jpg` | 直流通路：把 C_b1 画成断开（开路），输入支路去掉，只留 V_DD–R_d–管子 + R_g1/R_g2 分压 | 说明“电容开路、栅极电流为 0”，标出 V_G、V_GS、V_DS、I_D |
| `mos_small_signal.jpg` | 小信号等效模型 | R_g = R_g1∥R_g2 = 24 kΩ（接栅极到地）、受控电流源 g_m·v_gs（从漏极到源极）、r_o（与它并联）、R_d（漏极到地）、输出 v_o 在漏极、v_gs 的 +/− 极性 |

## 附：如果跑不通，最可能的四个原因

1. **提示「没找到 ngspice」**：`ngspice.dll` 不在脚本的搜索范围里。要么把它放到 `进阶挑战\..\ngspice\Spice64\Library\bin\`，
   要么设 `NGSPICE_LIBRARY_PATH` + `SPICE_LIB_DIR`（两个一起设，见 7.6 第 2 条）。
2. **`ModuleNotFoundError: No module named 'PySpice'` 或 'cffi'**：包没装到这个 Python 里。
   一律用 `python -m pip install PySpice numpy matplotlib cffi`，再用 `python -m pip list` 确认。
3. **`pip install PySpice` 装的是旧版（0.4.x 之类）**：API 不一样。用 `python -m pip show PySpice` 确认是 1.5 左右。
4. **找不到图和 CSV**：三个脚本都用 `HERE = os.path.dirname(os.path.abspath(__file__))` 定位自己所在目录，
   `figures/` 是建在**脚本旁边**（不是你当前命令行所在目录），所以去 `进阶挑战/figures/` 找。
