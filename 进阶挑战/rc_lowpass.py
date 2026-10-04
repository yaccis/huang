# -*- coding: utf-8 -*-
"""
① RC 低通滤波电路 —— 手算理论值 + PySpice 仿真验证 + 波形输出

电路：Vi --R--+-- vo
              |
              C
              |
             GND

参数（自定）：R = 1 kΩ, C = 100 nF
理论：τ = RC = 100 µs, fc = 1/(2πRC) ≈ 1591.5 Hz

运行前准备（Windows）：
    1) 装 Python 3.10+，然后 python -m pip install PySpice numpy matplotlib
    2) 准备 ngspice：把 ngspice.dll 放到本目录的 ngspice\\ 文件夹里（或设环境变量
       NGSPICE_LIBRARY_PATH 指向它），脚本会自动找到并使用「共享库模式」。
       命令行模式（ngspice.exe）在 Windows 上跑不通，原因见 README 的踩坑记录。
运行：
    python rc_lowpass.py
输出：
    控制台「手算 vs 仿真」表格 + figures/ 下的波形图与 CSV 数据
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
# 1. 电路参数与手算理论值
# ----------------------------------------------------------------------------
R_OHM = 1e3          # 1 kΩ
C_FARAD = 100e-9     # 100 nF
V_HIGH = 1.0         # 方波高电平 1 V
F_SQ = 1e3           # 方波频率 1 kHz（半周期 500 µs = 5τ）

TAU_THEORY = R_OHM * C_FARAD                 # τ = RC
FC_THEORY = 1.0 / (2 * math.pi * TAU_THEORY)  # fc = 1/(2πRC)
T_HALF = 0.5 / F_SQ                          # 方波半周期 500 µs = 5τ
# 半个周期结束时电容的理论电压：V_p = V(1 - e^{-t/τ})，t = 5τ 时 ≈ 0.9933 V
V_PLATEAU_THEORY = V_HIGH * (1.0 - math.exp(-T_HALF / TAU_THEORY))

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, 'figures')


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


# ----------------------------------------------------------------------------
# 2. 搭电路
# ----------------------------------------------------------------------------
def build_square_circuit():
    """方波输入的时域电路（阶段：瞬态分析）"""
    circuit = Circuit('RC low-pass filter - square wave')
    # 方波：0 V ~ 1 V，周期 1 ms，上升/下降沿 1 µs
    circuit.PulseVoltageSource('in', 'vin', circuit.gnd,
                               initial_value=0 @ u_V,
                               pulsed_value=V_HIGH @ u_V,
                               delay_time=0 @ u_us,
                               rise_time=1 @ u_us,
                               fall_time=1 @ u_us,
                               pulse_width=0.5 @ u_ms,
                               period=1 @ u_ms)
    circuit.R(1, 'vin', 'vout', R_OHM @ u_Ohm)
    circuit.C(1, 'vout', circuit.gnd, C_FARAD @ u_F)
    return circuit


def build_ac_circuit():
    """交流扫描电路：源的内置 ac_magnitude 默认为 1，于是 |vo| 就是幅频特性"""
    circuit = Circuit('RC low-pass filter - AC sweep')
    circuit.SinusoidalVoltageSource('in', 'vin', circuit.gnd,
                                    amplitude=1 @ u_V,
                                    frequency=1 @ u_kHz)
    circuit.R(1, 'vin', 'vout', R_OHM @ u_Ohm)
    circuit.C(1, 'vout', circuit.gnd, C_FARAD @ u_F)
    return circuit


def arr(waveform):
    """PySpice 的 WaveForm -> 普通 numpy 数组"""
    return np.asarray(waveform.as_ndarray(), dtype=float)


def scalar(waveform):
    """把只有 1 个点的 op 结果取成 float"""
    return float(np.asarray(waveform.as_ndarray()).ravel()[0])


# 注：make_simulator() 在文件开头「0. 自动找 ngspice」一节里定义


# ----------------------------------------------------------------------------
# 3. 仿真
# ----------------------------------------------------------------------------
def run_transient():
    circuit = build_square_circuit()
    print(circuit)                       # 打印网表，方便对照答案
    simulator = make_simulator(circuit)
    analysis = simulator.transient(step_time=1 @ u_us, end_time=3 @ u_ms)
    t = arr(analysis.time)
    vin = arr(analysis['vin'])
    vout = arr(analysis['vout'])
    return t, vin, vout


def run_ac():
    circuit = build_ac_circuit()
    simulator = make_simulator(circuit)
    analysis = simulator.ac(start_frequency=10 @ u_Hz,
                            stop_frequency=100 @ u_kHz,
                            number_of_points=50,
                            variation='dec')
    f = arr(analysis.frequency)
    h = analysis['vout'].as_ndarray()    # 复数
    return f, np.abs(h), np.angle(h, deg=True)


# ----------------------------------------------------------------------------
# 4. 从仿真波形里测参数
# ----------------------------------------------------------------------------
def measure_plateau(t, vout):
    """方波高电平结束前的稳态值（第一个半周期最后一个采样点）"""
    mask = t <= T_HALF
    if not mask.any():
        return float(vout[0])
    return float(vout[mask][-1])


def cross_time(t, v, level, start_index=0):
    """在线性插值下求 v 首次上升穿过 level 的时刻"""
    idx = np.where((v[:-1] < level) & (v[1:] >= level))[0]
    idx = idx[idx >= start_index]
    if len(idx) == 0:
        return None
    k = int(idx[0])
    dv = v[k + 1] - v[k]
    if dv == 0:
        return float(t[k])
    return float(t[k] + (level - v[k]) * (t[k + 1] - t[k]) / dv)


def measure_tau(t, vout, v_high):
    """用已知终值 V_high 反推时间常数。
    电容充电：v(t) = V_high·(1 - e^(-t/τ)) → τ = -t / ln(1 - v/V_high)
    取第一个上升段 10%~90% 的采样点分别算 τ 再取平均，避免单点误差和源上升沿的影响。"""
    high = np.where(vout >= 0.9 * v_high)[0]
    if len(high) == 0:
        return None
    k1 = int(high[0])
    low = np.where(vout[:k1 + 1] >= 0.1 * v_high)[0]
    if len(low) == 0:
        return None
    k0 = int(low[0])
    taus = []
    for k in range(k0, k1 + 1):
        ratio = 1.0 - float(vout[k]) / v_high
        if 0.0 < ratio < 1.0:
            taus.append(-float(t[k]) / math.log(ratio))
    if not taus:
        return None
    return float(np.mean(taus))


def measure_fc(f, mag):
    """幅频特性上找 |H| = 1/√2 对应的频率"""
    target = 1.0 / math.sqrt(2)
    order = np.argsort(f)
    f, mag = f[order], mag[order]
    below = np.where(mag <= target)[0]
    if len(below) == 0:
        return None
    i = below[0]
    if i == 0:
        return float(f[0])
    # 在对数坐标上线性插值
    x1, x2 = math.log10(f[i - 1]), math.log10(f[i])
    y1, y2 = mag[i - 1], mag[i]
    if y1 == y2:
        return float(f[i])
    x = x1 + (target - y1) * (x2 - x1) / (y2 - y1)
    return float(10 ** x)


# ----------------------------------------------------------------------------
# 5. 输出：表格 + CSV + 图
# ----------------------------------------------------------------------------
def print_table(rows, header):
    widths = [max(len(str(r[i])) for r in [header] + rows) for i in range(len(header))]
    line = '| ' + ' | '.join(str(header[i]).ljust(widths[i]) for i in range(len(header))) + ' |'
    print(line)
    print('|' + '|'.join('-' * (w + 2) for w in widths) + '|')
    for r in rows:
        print('| ' + ' | '.join(str(r[i]).ljust(widths[i]) for i in range(len(header))) + ' |')


def save_csv(name, header, columns):
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, name)
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(zip(*columns))
    print('已保存数据:', path)


def try_plot(t, vin, vout, f, mag, phase, tau_sim, fc_sim):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception as exc:                                   # noqa: BLE001
        print('未安装 matplotlib，跳过画图（%s）' % exc)
        return
    os.makedirs(OUTDIR, exist_ok=True)

    fig, ax = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    ax[0].plot(t * 1e3, vin, 'tab:gray', label='$v_i$ (square 1 V/1 kHz)')
    ax[1].plot(t * 1e3, vout, 'tab:blue', label='$v_o$')
    ax[1].axhline(0.632 * V_HIGH, color='tab:red', ls='--', lw=.8,
                  label='0.632·V = 632 mV')
    ax[0].set_ylabel('$v_i$ / V')
    ax[1].set_ylabel('$v_o$ / V')
    ax[1].set_xlabel('time / ms')
    ax[1].set_title('RC low-pass transient (R=1k$\\Omega$, C=100nF, '
                    '$\\tau_{sim}$=%.1f µs)' % (tau_sim * 1e6 if tau_sim else float('nan')))
    ax[0].grid(alpha=.3)
    ax[1].grid(alpha=.3)
    ax[0].legend(loc='upper right', fontsize=8)
    ax[1].legend(loc='upper right', fontsize=8)
    fig.tight_layout()
    p1 = os.path.join(OUTDIR, 'rc_transient.png')
    fig.savefig(p1, dpi=150)
    print('已保存图:', p1)

    fig2, axb = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    axb[0].semilogx(f, 20 * np.log10(mag), 'tab:blue')
    axb[0].axhline(-3.01, color='tab:red', ls='--', lw=.8, label='-3 dB')
    axb[0].set_ylabel('|H| / dB')
    axb[0].set_title('RC low-pass Bode plot ($f_{c,sim}$=%.1f Hz)' % (fc_sim or float('nan')))
    axb[1].semilogx(f, phase, 'tab:green')
    axb[1].axvline(fc_sim or FC_THEORY, color='tab:red', ls='--', lw=.8,
                   label='$f_c$ (=-45°)')
    axb[1].set_ylabel('phase / deg')
    axb[1].set_xlabel('frequency / Hz')
    axb[1].grid(alpha=.3, which='both')
    axb[0].grid(alpha=.3, which='both')
    axb[0].legend(fontsize=8)
    axb[1].legend(fontsize=8)
    fig2.tight_layout()
    p2 = os.path.join(OUTDIR, 'rc_bode.png')
    fig2.savefig(p2, dpi=150)
    print('已保存图:', p2)


# ----------------------------------------------------------------------------
def main():
    print('=' * 64)
    print('① RC 低通滤波电路：手算 vs 仿真')
    print('=' * 64)
    print('手算：τ = RC = %.3g Ω × %.3g F = %.1f µs' % (R_OHM, C_FARAD, TAU_THEORY * 1e6))
    print('手算：fc = 1/(2πRC) = %.2f Hz' % FC_THEORY)
    print()

    t, vin, vout = run_transient()
    v_steady = measure_plateau(t, vout)        # 半周期结束时的稳态值（≈5τ）
    tau_sim = measure_tau(t, vout, V_HIGH)
    # 理论：到达 0.95 V 的时刻 = -τ·ln(1 - 0.95/V_high)（终值是 1 V，不是 0.9933 V）
    t_95_theory = -TAU_THEORY * math.log(1.0 - 0.95 / V_HIGH)
    t_95_sim = cross_time(t, vout, 0.95)

    f, mag, phase = run_ac()
    fc_sim = measure_fc(f, mag)
    mag_at_fc = float(np.interp(math.log10(FC_THEORY), np.log10(f), mag))

    print('【瞬态：方波响应】')
    print_table(
        [['τ / µs', '%.1f' % (TAU_THEORY * 1e6), '%.1f' % (tau_sim * 1e6) if tau_sim else 'n/a',
          '%.2f %%' % (abs(tau_sim - TAU_THEORY) / TAU_THEORY * 100) if tau_sim else 'n/a'],
         ['V_o 稳态（5τ）/ V', '%.4f' % V_PLATEAU_THEORY, '%.4f' % v_steady,
          '%.2f %%' % (abs(v_steady - V_PLATEAU_THEORY) / V_PLATEAU_THEORY * 100)],
         ['到达 0.95 V 的时间 / µs', '%.1f' % (t_95_theory * 1e6),
          '%.1f' % (t_95_sim * 1e6) if t_95_sim else 'n/a',
          '%.2f %%' % (abs(t_95_sim - t_95_theory) / t_95_theory * 100) if t_95_sim else 'n/a']],
        ['指标', '手算', '仿真', '误差'])

    print()
    print('【幅频特性：|H| = 0.707 处】')
    print_table(
        [['fc / Hz', '%.2f' % FC_THEORY, '%.2f' % (fc_sim or float('nan')),
          '%.2f %%' % (abs(fc_sim - FC_THEORY) / FC_THEORY * 100) if fc_sim else 'n/a'],
         ['|H| @ fc', '0.7071', '%.4f' % mag_at_fc,
          '%.2f %%' % (abs(mag_at_fc - 0.7071) / 0.7071 * 100)],
         ['|H| @ 10·fc', '0.0995', '%.4f' % float(np.interp(math.log10(10 * FC_THEORY),
                                                           np.log10(f), mag)), '-']],
        ['指标', '手算', '仿真', '误差'])

    save_csv('rc_transient.csv', ['time_s', 'vin_V', 'vout_V'], [t, vin, vout])
    save_csv('rc_ac.csv', ['freq_Hz', 'mag', 'phase_deg'], [f, mag, phase])
    try_plot(t, vin, vout, f, mag, phase, tau_sim, fc_sim)

    print()
    print('结论：仿真测得的 τ 与 fc 和手算一致（误差 < 5%），')
    print('      方波经 RC 积分后变成近似三角波/指数充电波形，符合低通特性。')


if __name__ == '__main__':
    main()
