# -*- coding: utf-8 -*-
r"""
② 验证戴维南定理 —— 手算 V_th / R_th / I_sc + PySpice 两次仿真 + 接负载验证

含源二端网络（自定参数）：

        R1 = 1 kΩ
    o---[ R1 ]---+-------------------o  端口 a
                 |
   (V1 = 12 V)   +---[ R2 = 2 kΩ ]---+
                 |                   |
                 |              (V2 = 6 V)
                 |
                 +---[ R3 = 3 kΩ ]---+
                 |                   |
                GND                  o  端口 b (GND)

    （V1 通过 R1 接到 a 点，V2 通过 R2 接到 a 点，R3 从 a 点到地；
      a、b 就是待等效的端口。）

手算（节点电压法，取 a 点）：
    Va·(1/R1 + 1/R2 + 1/R3) = V1/R1 + V2/R2
    1/R1+1/R2+1/R3 = 1/1000+1/2000+1/3000 = 11/6000 S
    V1/R1 + V2/R2 = 12/1000 + 6/2000 = 15 mA
    V_th = V_oc = Va = 15 mA / (11/6000) = 90/11 ≈ 8.1818 V
    R_th = R1∥R2∥R3 = 6000/11 ≈ 545.45 Ω   （电压源置零 → 短路）
    I_sc = V_th / R_th = 15 mA

运行前准备（Windows）：
    1) 装 Python 3.10+，然后 python -m pip install PySpice numpy matplotlib
    2) 准备 ngspice：把 ngspice.dll 放到本目录的 ngspice\ 文件夹里（或设环境变量
       NGSPICE_LIBRARY_PATH 指向它），脚本会自动找到并使用「共享库模式」。
       命令行模式（ngspice.exe）在 Windows 上跑不通，原因见 README 的踩坑记录。
运行：python thevenin.py
"""

import math
import os
import csv

import numpy as np

from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

import sys

# 中文 Windows 控制台/重定向输出时，打印 µ、Ω 等字符可能触发 GBK 编码错误，这里兜底
try:
    sys.stdout.reconfigure(errors='replace')
except Exception:
    pass

# ----------------------------------------------------------------------------
# 电路参数（自定）
# ----------------------------------------------------------------------------
V1, R1 = 12.0, 1e3      # 12 V 串 1 kΩ
V2, R2 = 6.0, 2e3       # 6 V 串 2 kΩ
R3 = 3e3                # 3 kΩ 接端口
LOADS = [1e3, 470.0, 2.2e3]   # 接负载验证用的三个负载

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, 'figures')


# ----------------------------------------------------------------------------
# 1. 手算
# ----------------------------------------------------------------------------
def hand_calc():
    v_oc = (V1 / R1 + V2 / R2) / (1 / R1 + 1 / R2 + 1 / R3)   # 开路电压
    r_th = 1.0 / (1 / R1 + 1 / R2 + 1 / R3)                    # 等效内阻
    i_sc = v_oc / r_th                                         # 短路电流
    return v_oc, r_th, i_sc


def hand_loaded(v_oc, r_th, rl):
    i_l = v_oc / (r_th + rl)
    return i_l * rl, i_l


# ----------------------------------------------------------------------------
# 2. 仿真
# ----------------------------------------------------------------------------
def build_network(load=None):
    """load=None 开路；'short' 短路；数值则接该负载"""
    circuit = Circuit('Thevenin source network')
    circuit.V(1, 'n1', circuit.gnd, V1 @ u_V)
    circuit.R(1, 'n1', 'a', R1 @ u_Ohm)
    circuit.V(2, 'n2', circuit.gnd, V2 @ u_V)
    circuit.R(2, 'n2', 'a', R2 @ u_Ohm)
    circuit.R(3, 'a', circuit.gnd, R3 @ u_Ohm)
    if load == 'short':
        # 0 V 电压源 = 理想电流表，端口短路，读它的支路电流即 I_sc
        circuit.V('sc', 'a', circuit.gnd, 0 @ u_V)
    elif load is not None:
        circuit.R('L', 'a', circuit.gnd, load @ u_Ohm)
    return circuit


def build_thevenin(v_th, r_th, load):
    """戴维南等效电路 + 同一负载"""
    circuit = Circuit('Thevenin equivalent')
    circuit.V('th', 'x', circuit.gnd, v_th @ u_V)
    circuit.R('th', 'x', 'a', r_th @ u_Ohm)
    circuit.R('L', 'a', circuit.gnd, load @ u_Ohm)
    return circuit


def op(circuit):
    simulator = make_simulator(circuit)
    return simulator.operating_point()


# ----------------------------------------------------------------------------
# 0. 自动找 ngspice + 选运行模式
#    Windows 版 ngspice 的命令行服务器模式（ngspice -s）目前有两个坑：
#      ① 自带 spinit 里写着 set filetype=ascii，rawfile 输出成纯文本，而 PySpice 只认二进制段；
#      ② 输出开头多一行 "Note: ..."，而 PySpice 的头部解析要求第一行就是 "Circuit:"。
#    所以 Windows 上改用 PySpice 的共享库模式（ngspice.dll），这也是 PySpice 在 Windows 的默认模式。
# ----------------------------------------------------------------------------
def _find_ngspice(patterns):
    import glob
    roots = []
    for key in ('NGSPICE_LIBRARY_PATH', 'NGSPICE_EXE', 'NGSPICE_HOME'):
        value = os.environ.get(key)
        if value:
            roots.append(value if os.path.isdir(value) else os.path.dirname(value))
    roots += [HERE,
              os.path.join(HERE, 'ngspice'),
              os.path.join(os.path.dirname(HERE), 'ngspice'),
              os.path.join(os.path.dirname(HERE), 'ngspice_runtime'),
              r'D:\ngspice', r'C:\ngspice', r'D:\Spice64', r'C:\Spice64',
              r'C:\Program Files\ngspice']
    for root in roots:                              # 先按固定目录结构找（快）
        for sub in (('Spice64', 'Library', 'bin'), ('Spice64', 'bin'), ('Library', 'bin'),
                    ('bin',), ('Spice64_dll', 'dll-vs'), ()):
            for pattern in patterns:
                hit = os.path.join(root, *sub, pattern)
                if '*' not in hit and os.path.isfile(hit):
                    return os.path.abspath(hit)
    for root in roots:                              # 再在常见根目录里递归找一遍
        if not os.path.isdir(root):
            continue
        for pattern in patterns:
            for hit in sorted(glob.glob(os.path.join(root, '**', pattern), recursive=True)):
                if os.path.isfile(hit):
                    return os.path.abspath(hit)
    return None


NGSPICE_DLL = _find_ngspice(['ngspice*.dll'])
NGSPICE_EXE = _find_ngspice(['ngspice_con.exe', 'ngspice.exe'])
NGSPICE_INIT = os.path.join(HERE, 'ngspice_init')     # 本目录下的精简 spinit
if os.path.isfile(os.path.join(NGSPICE_INIT, 'scripts', 'spinit')):
    os.environ.setdefault('SPICE_LIB_DIR', NGSPICE_INIT)
if NGSPICE_DLL:
    os.environ.setdefault('NGSPICE_LIBRARY_PATH', NGSPICE_DLL)
SIMULATOR = os.environ.get('SPICE_SIMULATOR') or ('ngspice-shared' if NGSPICE_DLL else 'ngspice-subprocess')


def make_simulator(circuit):
    """建 simulator：找到 ngspice.dll 就用共享库模式，否则回退命令行模式。"""
    kwargs = dict(temperature=25, nominal_temperature=25, simulator=SIMULATOR)
    if SIMULATOR == 'ngspice-subprocess' and NGSPICE_EXE:
        kwargs['spice_command'] = NGSPICE_EXE
    if SIMULATOR == 'ngspice-shared':
        print('  [ngspice] 共享库模式，ngspice.dll = %s' % NGSPICE_DLL)
    elif NGSPICE_EXE:
        print('  [ngspice] 命令行模式，ngspice = %s' % NGSPICE_EXE)
    else:
        print('  [ngspice] 没找到 ngspice！请把 ngspice.dll 放进本目录的 ngspice\\ 里，'
              '或设 NGSPICE_LIBRARY_PATH 指向它')
    return circuit.simulator(**kwargs)


def scalar(waveform):
    return float(np.asarray(waveform.as_ndarray()).ravel()[0])


def branch_current(analysis, name):
    """按名字取电压源支路电流（大小写不敏感）"""
    for key, waveform in analysis.branches.items():
        if key.lower() == name.lower():
            return abs(scalar(waveform))
    raise KeyError(name)


def sim_open():
    a = op(build_network(None))
    return scalar(a['a'])                       # 开路电压 V_oc


def sim_short():
    a = op(build_network('short'))
    try:
        i_sc = branch_current(a, 'vsc')         # 支路电流
        method = '0 V 电流表'
    except Exception:                           # noqa: BLE001
        # 保险起见：用 1 mΩ 近似短路，误差 ~1e-6
        circuit = build_network(None)
        circuit.R('short', 'a', circuit.gnd, 1e-3 @ u_Ohm)
        va = scalar(op(circuit)['a'])
        i_sc, method = va / 1e-3, '1 mΩ 近似短路'
    return abs(i_sc), method


def sim_loaded(load, thevenin=False, v_th=0.0, r_th=0.0):
    circuit = (build_thevenin(v_th, r_th, load) if thevenin
               else build_network(load))
    a = op(circuit)
    v_l = scalar(a['a'])
    return v_l, v_l / load


# ----------------------------------------------------------------------------
# 3. 打印
# ----------------------------------------------------------------------------
def print_table(header, rows):
    widths = [max(len(str(r[i])) for r in [header] + rows) for i in range(len(header))]
    print('| ' + ' | '.join(str(header[i]).ljust(widths[i]) for i in range(len(header))) + ' |')
    print('|' + '|'.join('-' * (w + 2) for w in widths) + '|')
    for r in rows:
        print('| ' + ' | '.join(str(r[i]).ljust(widths[i]) for i in range(len(header))) + ' |')


def pct(sim, hand):
    return '%.2f %%' % (abs(sim - hand) / abs(hand) * 100)


def main():
    print('=' * 68)
    print('② 戴维南定理验证：手算 vs 仿真')
    print('=' * 68)
    v_oc, r_th, i_sc = hand_calc()
    print('手算：V_th = V_oc = (V1/R1 + V2/R2) / (1/R1 + 1/R2 + 1/R3) = %.4f V' % v_oc)
    print('手算：R_th = R1∥R2∥R3 = %.2f Ω' % r_th)
    print('手算：I_sc = V_th / R_th = %.4f mA' % (i_sc * 1e3))
    print()

    voc_sim = sim_open()
    isc_sim, method = sim_short()
    r_th_sim = voc_sim / isc_sim

    print('【仿真一：开路 / 短路（两次独立仿真）】')
    print_table(['量', '手算值', '仿真值', '误差'],
                [['V_oc / V', '%.4f' % v_oc, '%.4f' % voc_sim, pct(voc_sim, v_oc)],
                 ['I_sc / mA', '%.4f' % (i_sc * 1e3), '%.4f' % (isc_sim * 1e3),
                  pct(isc_sim, i_sc)]])
    print('    （短路电流用 %s 测得）' % method)
    print()
    print('【由仿真值反推等效内阻】')
    print_table(['量', '手算值', '仿真值', '误差'],
                [['R_th / Ω', '%.2f' % r_th, '%.2f' % r_th_sim, pct(r_th_sim, r_th)]])
    print()

    print('【仿真二：等效电路替换后接负载的验证】')
    rows = []
    for rl in LOADS:
        v_hand, i_hand = hand_loaded(v_oc, r_th, rl)
        v_sim, i_sim = sim_loaded(rl)
        v_eq, i_eq = sim_loaded(rl, thevenin=True, v_th=v_oc, r_th=r_th)
        rows.append(['R_L = %s' % ('%.0f Ω' % rl if rl >= 1 else '%.1f Ω' % rl),
                     '%.4f V / %.4f mA' % (v_hand, i_hand * 1e3),
                     '%.4f V / %.4f mA' % (v_sim, i_sim * 1e3),
                     '%.4f V / %.4f mA' % (v_eq, i_eq * 1e3),
                     pct(v_sim, v_hand)])
    print_table(['负载', '手算 (V_L / I_L)', '原网络仿真', '戴维南等效仿真', '误差'], rows)
    print()
    print('结论：原网络与“V_th 串联 R_th”的等效电路在同一负载下电压/电流完全一致，')
    print('      误差只来自数值精度，戴维南定理得到验证。')

    # ---- 外特性曲线（可选，需要 matplotlib）----
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, 'thevenin_load.csv'), 'w', newline='',
              encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['R_L_ohm', 'V_L_hand_V', 'V_L_sim_V', 'I_L_hand_mA', 'I_L_sim_mA'])
        for rl in LOADS + [100.0, 10e3]:
            vh, ih = hand_loaded(v_oc, r_th, rl)
            vs, isim = sim_loaded(rl)
            w.writerow([rl, vh, vs, ih * 1e3, isim * 1e3])
    print('已保存数据:', os.path.join(OUTDIR, 'thevenin_load.csv'))

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        rls = np.logspace(1, 4, 25)
        vs = [sim_loaded(float(r))[0] for r in rls]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.semilogx(rls, [hand_loaded(v_oc, r_th, float(r))[0] for r in rls],
                    '-', label='hand (V_th=%.3f V, R_th=%.1f $\\Omega$)' % (v_oc, r_th))
        ax.semilogx(rls, vs, 'o', ms=3, label='PySpice simulation')
        ax.axhline(v_oc, color='gray', ls=':', lw=.8)
        ax.set_xlabel('$R_L$ / $\\Omega$')
        ax.set_ylabel('$V_L$ / V')
        ax.set_title('Thevenin verification: load characteristic')
        ax.grid(alpha=.3, which='both')
        ax.legend(fontsize=8)
        fig.tight_layout()
        path = os.path.join(OUTDIR, 'thevenin_load.png')
        fig.savefig(path, dpi=150)
        print('已保存图:', path)
    except Exception as exc:                                   # noqa: BLE001
        print('未安装 matplotlib，跳过画图（%s）' % exc)


if __name__ == '__main__':
    main()
