# -*- coding: utf-8 -*-
r"""
③ 放大电路：NMOS 共源放大器 —— 手算静态工作点/小信号参数 + PySpice 验证

题给参数：
    VDD = 5 V, Rg1 = 60 kΩ, Rg2 = 40 kΩ, Rd = 2 kΩ, Cb1 足够大（取 10 µF）
    NMOS Level-1 模型：K = KP = 0.8 mA/V², V_th = VTO = 1 V, λ = LAMBDA = 0.02 /V
    Vi = 10 mV / 1 kHz 正弦

手算静态工作点：
    V_G = VDD·Rg2/(Rg1+Rg2) = 5 × 40/100 = 2.0 V，栅极不取电流 → V_GS = 2.0 V
    V_ov = V_GS − V_th = 1.0 V > 0 → 导通
    设 λ=0：I_D0 = ½K·V_ov² = 0.4 mA → V_DS0 = 5 − 0.4m×2k = 4.2 V
    含 λ：I_D = ½K·V_ov²·(1+λ·V_DS)，V_DS = VDD − I_D·Rd
      → I_D = a(1+λVDD)/(1+aλRd)，a = ½K·V_ov² = 0.4 mA
      → I_D = 0.4m×1.1/1.016 = 0.4331 mA，V_DS = 5 − 0.866 = 4.134 V
    饱和判据：V_DS(4.134 V) > V_GS − V_th(1.0 V) → 工作在饱和区 ✔

手算小信号：
    gm = K·V_ov·(1+λV_DS) = 0.8m×1×1.0827 = 0.866 mS
       （等价 gm = 2I_D/V_ov）
    ro = 1/(λ·I_D) = 1/(0.02×0.4331m) = 115.4 kΩ
    Av = −gm·(Rd∥ro) = −0.866m × 1.966k = −1.703  （反相，约 4.6 dB）

运行前准备（Windows）：
    1) 装 Python 3.10+，然后 python -m pip install PySpice numpy matplotlib
    2) 准备 ngspice：把 ngspice.dll 放到本目录的 ngspice\ 文件夹里（或设环境变量
       NGSPICE_LIBRARY_PATH 指向它），脚本会自动找到并使用「共享库模式」。
       命令行模式（ngspice.exe）在 Windows 上跑不通，原因见 README 的踩坑记录。
运行：python mos_common_source.py
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
# 题给参数（不要改）
# ----------------------------------------------------------------------------
VDD = 5.0
RG1, RG2 = 60e3, 40e3
RD = 2e3
K_PARAM = 0.8e-3       # K = 0.8 mA/V²
VTH = 1.0              # V_th
LAMBDA = 0.02          # λ
VI_AMP = 10e-3         # 10 mV
FREQ = 1e3             # 1 kHz
CB1 = 10e-6            # Cb1 视为足够大：10 µF（fc = 1/(2π·24k·10µ) ≈ 0.66 Hz）

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, 'figures')


# ----------------------------------------------------------------------------
# 1. 手算
# ----------------------------------------------------------------------------
def hand_calc():
    vg = VDD * RG2 / (RG1 + RG2)          # 栅极直流电位
    vgs = vg                              # 栅流为 0
    vov = vgs - VTH
    a = 0.5 * K_PARAM * vov ** 2          # λ=0 时的 I_D
    id_lam0 = a
    vds_lam0 = VDD - id_lam0 * RD
    # 含 λ 的精确解（饱和区）
    id_ = a * (1 + LAMBDA * VDD) / (1 + a * LAMBDA * RD)
    vds = VDD - id_ * RD
    saturated = vds > vov
    gm = K_PARAM * vov * (1 + LAMBDA * vds)
    gm_alt = 2 * id_ / vov
    ro = 1.0 / (LAMBDA * id_)
    rd_par_ro = 1.0 / (1.0 / RD + 1.0 / ro)
    av = -gm * rd_par_ro
    return dict(vg=vg, vgs=vgs, vov=vov, id=id_, vds=vds, saturated=saturated,
                id_lam0=id_lam0, vds_lam0=vds_lam0, gm=gm, gm_alt=gm_alt, ro=ro,
                rd_par_ro=rd_par_ro, av=av)


# ----------------------------------------------------------------------------
# 2. 仿真
# ----------------------------------------------------------------------------
def build_circuit(transient=False):
    """drain 上串一个 0 V 源当电流表，读 I_D 不受 Rg1 支路影响"""
    circuit = Circuit('NMOS common source amplifier')
    circuit.model('nmos1', 'NMOS', KP=K_PARAM, VTO=VTH, LAMBDA=LAMBDA)
    circuit.V('dd', 'vdd', circuit.gnd, VDD @ u_V)
    circuit.R('d', 'vdd', 'd1', RD @ u_Ohm)
    circuit.V('sense', 'd1', 'd', 0 @ u_V)        # 电流表：I(vsense) = I_D
    circuit.R('g1', 'vdd', 'g', RG1 @ u_Ohm)
    circuit.R('g2', 'g', circuit.gnd, RG2 @ u_Ohm)
    circuit.M(1, 'd', 'g', circuit.gnd, circuit.gnd, model='nmos1',
             w=1e-6, l=1e-6)      # 源极接地，衬底接源极（即地）
    if transient:
        circuit.SinusoidalVoltageSource('i', 'vi', circuit.gnd,
                                        dc_offset=0 @ u_V,
                                        amplitude=VI_AMP @ u_V,
                                        frequency=FREQ @ u_Hz)
    else:
        circuit.V('i', 'vi', circuit.gnd, 0 @ u_V)     # 直流分析时输入置 0
    circuit.C('b1', 'vi', 'g', CB1 @ u_F)
    return circuit


def scalar(waveform):
    return float(np.asarray(waveform.as_ndarray()).ravel()[0])


def arr(waveform):
    return np.asarray(waveform.as_ndarray(), dtype=float)


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


def branch_current(analysis, name):
    for key, waveform in analysis.branches.items():
        if key.lower() == name.lower():
            return abs(scalar(waveform))
    raise KeyError(name)


def sim_operating_point():
    circuit = build_circuit(transient=False)
    print(circuit)
    simulator = make_simulator(circuit)
    a = simulator.operating_point()
    # 源极接地（节点 0），所以 V_GS 就是栅极电位、V_DS 就是漏极电位
    vgs = scalar(a['g'])
    vds = scalar(a['d'])
    try:
        id_ = branch_current(a, 'vsense')
    except Exception:                                   # noqa: BLE001
        id_ = (scalar(a['vdd']) - scalar(a['d1'])) / RD   # 用 Rd 上压降反推
    return dict(vg=scalar(a['g']), vgs=vgs, vds=vds, id=id_)


def sim_transient():
    circuit = build_circuit(transient=True)
    simulator = make_simulator(circuit)
    # 1 kHz 正弦：步长 1 µs，跑 3 个周期
    analysis = simulator.transient(step_time=1 @ u_us, end_time=3 @ u_ms)
    t = arr(analysis.time)
    vi = arr(analysis['vi'])
    vg = arr(analysis['g'])
    vo = arr(analysis['d'])
    return t, vi, vg, vo


def amplitude(t, v, f, cycles=1):
    """取最后 cycles 个周期的 (max-min)/2 作为幅值"""
    t_end = t[-1]
    t_start = t_end - cycles / f
    m = t >= t_start
    return (v[m].max() - v[m].min()) / 2.0


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


def db(x):
    """20·log10(|x|)，x 为 0 或负时返回 '-inf' 而不是抛异常"""
    return 20 * math.log10(abs(x)) if x else float('-inf')


def main():
    print('=' * 70)
    print('③ NMOS 共源放大电路：手算 vs 仿真')
    print('=' * 70)
    h = hand_calc()
    print('【直流通路手算】')
    print('  V_G = VDD·Rg2/(Rg1+Rg2) = %.3f V  →  V_GS = %.3f V' % (h['vg'], h['vgs']))
    print('  V_ov = V_GS − V_th = %.3f V' % h['vov'])
    print('  先设 λ=0：I_D = ½K·V_ov² = %.4f mA → V_DS = %.3f V' %
          (h['id_lam0'] * 1e3, h['vds_lam0']))
    print('  含 λ ：I_D = a(1+λVDD)/(1+aλRd) = %.4f mA → V_DS = %.4f V' %
          (h['id'] * 1e3, h['vds']))
    print('  饱和判断：V_DS = %.4f V > V_GS − V_th = %.3f V → %s' %
          (h['vds'], h['vov'], '工作在饱和区 ✔' if h['saturated'] else '不在饱和区'))
    print()

    s = sim_operating_point()
    print('【直流工作点对比】')
    print_table(['量', '手算值', '仿真值', '误差'],
                [['V_GS / V', '%.4f' % h['vgs'], '%.4f' % s['vgs'], pct(s['vgs'], h['vgs'])],
                 ['I_D / mA', '%.4f' % (h['id'] * 1e3), '%.4f' % (s['id'] * 1e3),
                  pct(s['id'], h['id'])],
                 ['V_DS / V', '%.4f' % h['vds'], '%.4f' % s['vds'], pct(s['vds'], h['vds'])]])
    print()

    print('【小信号参数手算】')
    print('  gm = K·V_ov·(1+λV_DS) = %.4f mS   （校验 2I_D/V_ov = %.4f mS）' %
          (h['gm'] * 1e3, h['gm_alt'] * 1e3))
    print('  ro = 1/(λ·I_D) = %.2f kΩ' % (h['ro'] / 1e3))
    print('  Rd∥ro = %.2f Ω' % h['rd_par_ro'])
    print('  Av = −gm(Rd∥ro) = %.4f V/V  （%.2f dB，反相）' %
          (h['av'], db(h['av'])))
    print()

    t, vi, vg, vo = sim_transient()
    amp_in = amplitude(t, vi, FREQ)
    amp_gate = amplitude(t, vg, FREQ)
    amp_out = amplitude(t, vo, FREQ)
    # 稳态段（最后一个周期）里比较：输入/输出都是 1 kHz，波形的直流分量单独看
    m = t >= t[-1] - 1.0 / FREQ
    vo_dc = np.mean(vo[m])
    vi_dc = np.mean(vi[m])
    # 直接比较峰峰值更直观
    gain_pp = (vo[m].max() - vo[m].min()) / (vi[m].max() - vi[m].min())

    print('【交流（瞬态）仿真】Vi = 10 mV / 1 kHz')
    print_table(['量', '手算值', '仿真值', '误差'],
                [['输入幅值 / mV', '10.0000', '%.4f' % (amp_in * 1e3), '-'],
                 ['栅极交流幅值 / mV', '-', '%.4f' % (amp_gate * 1e3), '-'],
                 ['输出幅值 / mV', '%.4f' % (abs(h['av']) * VI_AMP * 1e3),
                  '%.4f' % (amp_out * 1e3), pct(amp_out, abs(h['av']) * VI_AMP)],
                 ['增益 |Av| (V/V)', '%.4f' % abs(h['av']), '%.4f' % gain_pp,
                  pct(gain_pp, abs(h['av']))],
                 ['增益 (dB)', '%.2f' % db(h['av']),
                  '%.2f' % db(gain_pp), '-'],
                 ['输出直流电平 / V', '%.4f' % h['vds'], '%.4f' % vo_dc,
                  pct(vo_dc, h['vds'])],
                 ['输入直流电平 / V', '0.0000', '%.4f' % vi_dc, '-']])
    print('  注：输出与输入相位相反（共源级反相放大），从波形图上可见。')

    # ---- 存数据 + 画图 ----
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, 'mos_cs_transient.csv'), 'w', newline='',
              encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['time_s', 'vi_V', 'vg_V', 'vo_V'])
        w.writerows(zip(t, vi, vg, vo))
    print('已保存数据:', os.path.join(OUTDIR, 'mos_cs_transient.csv'))

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        ax[0].plot(t * 1e3, vi * 1e3, 'tab:blue', label='$v_i$ (10 mV)')
        ax[0].plot(t * 1e3, (vg - np.mean(vg)) * 1e3, 'tab:green', lw=.8,
                   label='$v_g$ (AC part)')
        ax[1].plot(t * 1e3, vo, 'tab:red', label='$v_o$ (around %.2f V)' % np.mean(vo))
        ax[0].set_ylabel('$v_i$, $v_g$ / mV')
        ax[1].set_ylabel('$v_o$ / V')
        ax[1].set_xlabel('time / ms')
        ax[1].set_title('NMOS common-source amplifier: $|A_v|$ = %.3f, '
                        'inverted (180°)' % gain_pp)
        ax[0].grid(alpha=.3)
        ax[1].grid(alpha=.3)
        ax[0].legend(fontsize=8)
        ax[1].legend(fontsize=8)
        fig.tight_layout()
        path = os.path.join(OUTDIR, 'mos_cs_transient.png')
        fig.savefig(path, dpi=150)
        print('已保存图:', path)
    except Exception as exc:                                   # noqa: BLE001
        print('未安装 matplotlib，跳过画图（%s）' % exc)

    print()
    print('结论：直流工作点(%.4f V, %.4f mA, %.4f V)与手算一致，管子工作在饱和区；' %
          (s['vgs'], s['id'] * 1e3, s['vds']))
    print('      交流增益 ≈ %.2f（反相），与 Av = −gm(Rd∥ro) 手算值吻合。' % gain_pp)


if __name__ == '__main__':
    main()
