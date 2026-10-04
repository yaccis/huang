# -*- coding: utf-8 -*-
"""
draw_figures.py —— 生成「五、进阶挑战」需要的 6 张电路图。

用 matplotlib 的线条/矩形/圆手工画原理图，输出到 figures/ 下的 6 个 jpg：
    rc_circuit.jpg          ① RC 低通滤波电路
    thevenin_network.jpg    ② 原含源二端网络（标出端口 a、b）
    thevenin_equivalent.jpg ② 戴维南等效电路 + 负载 R_L
    mos_circuit.jpg         ③ NMOS 共源放大电路（题卡拓扑）
    mos_dc_path.jpg         ③ 直流通路（C_b1 开路）
    mos_small_signal.jpg    ③ 小信号等效模型

运行：python draw_figures.py     （需要 matplotlib）
"""
import os
import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager, rcParams
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, 'figures')

# 中文字体：用系统里的黑体（没有就退回雅黑），避免中文画成方框
for _p in (r'C:\Windows\Fonts\simhei.ttf', r'C:\Windows\Fonts\msyh.ttc',
           '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'):
    if os.path.exists(_p):
        try:
            font_manager.fontManager.addfont(_p)
        except Exception:
            pass
rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Zen Hei', 'DejaVu Sans']
rcParams['font.serif'] = rcParams['font.sans-serif']
rcParams['axes.unicode_minus'] = False

LW = 2.0
FS = 12.0          # 普通标注字号
FS_S = 10.5        # 小标注字号
TITLE_FS = 13.5
BOX = dict(boxstyle='round,pad=0.45', facecolor='#f4f4f4', edgecolor='0.6', lw=1.0)


# --------------------------------------------------------------------------
# 画图小工具
# --------------------------------------------------------------------------
def new_ax(w=9.0, h=5.4, xlim=(0, 10), ylim=(0, 6)):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect('equal')
    ax.axis('off')
    return fig, ax


def wire(ax, pts, lw=LW, ls='-', color='black'):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, solid_capstyle='round', solid_joinstyle='round')


def dot(ax, x, y, r=0.05):
    ax.add_patch(Circle((x, y), r, facecolor='black', edgecolor='none', zorder=6))


def term(ax, x, y, label=None, dx=0.24, dy=0.0, ha='left', va='center', fs=FS):
    ax.add_patch(Circle((x, y), 0.085, facecolor='white', edgecolor='black', lw=1.8, zorder=6))
    if label:
        ax.text(x + dx, y + dy, label, ha=ha, va=va, fontsize=fs, zorder=7)


def res_v(ax, x, y1, y2, label=None, side='right', fs=FS):
    """竖直电阻，本体画在 y2..y1 之间（y1 > y2），引线由调用方画。"""
    ax.add_patch(Rectangle((x - 0.16, y2), 0.32, y1 - y2, fill=False, lw=LW, edgecolor='black', zorder=5))
    if label:
        if side == 'right':
            ax.text(x + 0.32, (y1 + y2) / 2, label, ha='left', va='center', fontsize=fs, zorder=7)
        else:
            ax.text(x - 0.32, (y1 + y2) / 2, label, ha='right', va='center', fontsize=fs, zorder=7)


def res_h(ax, y, x1, x2, label=None, fs=FS):
    """水平电阻，本体画在 x1..x2 之间（x2 > x1）。"""
    ax.add_patch(Rectangle((x1, y - 0.16), x2 - x1, 0.32, fill=False, lw=LW, edgecolor='black', zorder=5))
    if label:
        ax.text((x1 + x2) / 2, y + 0.36, label, ha='center', va='center', fontsize=fs, zorder=7)


def cap_v(ax, x, y_top, y_bot, gap=0.11, half=0.26, color='black'):
    """竖直电容：两块水平极板，画在 y_top..y_bot 的中点两侧。"""
    mid = (y_top + y_bot) / 2
    for yy in (mid + gap, mid - gap):
        ax.plot([x - half, x + half], [yy, yy], color=color, lw=LW + 0.8, solid_capstyle='round', zorder=5)


def cap_h(ax, y, x_left, x_right, gap=0.11, half=0.26, color='black'):
    """水平电容：两块竖直极板。"""
    mid = (x_left + x_right) / 2
    for xx in (mid + gap, mid - gap):
        ax.plot([xx, xx], [y - half, y + half], color=color, lw=LW + 0.8, solid_capstyle='round', zorder=5)


def ground(ax, x, y, s=1.0):
    wire(ax, [(x, y), (x, y - 0.20)])
    for i, w in enumerate((0.22, 0.14, 0.07)):
        yy = y - 0.20 - 0.10 * i
        ax.plot([x - w * s, x + w * s], [yy, yy], color='black', lw=LW - 0.5, solid_capstyle='round')


def vsrc(ax, x, y1, y2, label=None, label_side='left', fs=FS):
    """竖直电压源（圆圈 + 正负号），本体画在 y1..y2 之间。"""
    cy = (y1 + y2) / 2
    ax.add_patch(Circle((x, cy), 0.45, facecolor='white', edgecolor='black', lw=LW, zorder=5))
    ax.text(x, cy + 0.19, '+', ha='center', va='center', fontsize=FS_S + 3, zorder=7)
    ax.text(x, cy - 0.21, '-', ha='center', va='center', fontsize=FS_S + 3, zorder=7)
    if label:
        if label_side == 'left':
            ax.text(x - 0.62, cy, label, ha='right', va='center', fontsize=fs, zorder=7)
        else:
            ax.text(x + 0.62, cy, label, ha='left', va='center', fontsize=fs, zorder=7)


def arrow(ax, x1, y1, x2, y2, style='-|>', lw=1.6, color='black', ms=12):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1), zorder=7,
                arrowprops=dict(arrowstyle=style, lw=lw, color=color,
                                shrinkA=0, shrinkB=0, mutation_scale=ms))


def label(ax, x, y, text, ha='left', va='center', fs=FS, rot=0, color='black', zorder=7, box=None):
    ax.text(x, y, text, ha=ha, va=va, fontsize=fs, rotation=rot, color=color, zorder=zorder, bbox=box)


def save(fig, name):
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, name)
    fig.savefig(path, dpi=150, facecolor='white', bbox_inches='tight', pil_kwargs={'quality': 92})
    plt.close(fig)
    print('已保存图:', path)


# --------------------------------------------------------------------------
# 图 1：RC 低通滤波电路
# --------------------------------------------------------------------------
def fig_rc_circuit():
    fig, ax = new_ax(9.0, 4.6, xlim=(-0.8, 9.6), ylim=(-0.9, 5.3))
    y_top, y_bot = 4.2, 0.6

    wire(ax, [(1.0, y_top), (2.4, y_top)])
    res_h(ax, y_top, 2.4, 4.4, '$R = 1\\,\\mathrm{k}\\Omega$')
    wire(ax, [(4.4, y_top), (7.6, y_top)])
    wire(ax, [(6.6, y_top), (6.6, y_bot)])
    cap_v(ax, 6.6, y_top, y_bot)
    label(ax, 6.24, 2.4, '$C = 100\\,\\mathrm{nF}$', ha='right')
    wire(ax, [(1.0, y_bot), (6.6, y_bot)])
    ground(ax, 3.6, y_bot)

    term(ax, 1.0, y_top)
    term(ax, 1.0, y_bot)
    term(ax, 7.6, y_top)
    term(ax, 7.6, y_bot)

    arrow(ax, 0.42, y_bot, 0.42, y_top, style='<->', lw=1.3)
    label(ax, 0.10, 2.4, '$v_i$', ha='center', rot=90, fs=FS + 1)
    label(ax, 0.62, 3.55, '+', ha='center')
    label(ax, 0.62, 1.25, '-', ha='center')
    arrow(ax, 8.15, y_bot, 8.15, y_top, style='<->', lw=1.3)
    label(ax, 8.52, 2.4, '$v_o$', ha='center', rot=90, fs=FS + 1)
    label(ax, 7.85, 3.55, '+', ha='center')
    label(ax, 7.85, 1.25, '-', ha='center')

    ax.set_title('图 1  RC 低通滤波电路（R = 1 kΩ，C = 100 nF）', fontsize=TITLE_FS, y=0.99)
    save(fig, 'rc_circuit.jpg')


# --------------------------------------------------------------------------
# 图 2：原含源二端网络
# --------------------------------------------------------------------------
def fig_thevenin_network():
    fig, ax = new_ax(9.6, 5.6, xlim=(-1.4, 10.2), ylim=(-0.2, 6.4))
    y_rail, y_top, y_mid = 0.8, 5.2, 3.6

    wire(ax, [(1.5, y_rail), (8.6, y_rail)])
    ground(ax, 2.4, y_rail)

    # 支路 1：V1 串 R1
    wire(ax, [(1.5, y_rail), (1.5, y_top)])
    vsrc(ax, 1.5, y_rail, y_top, '$V_1 = 12\\,\\mathrm{V}$', label_side='left')
    wire(ax, [(1.5, y_top), (2.8, y_top)])
    res_h(ax, y_top, 2.8, 4.2, '$R_1 = 1\\,\\mathrm{k}\\Omega$')
    wire(ax, [(4.2, y_top), (6.0, y_top), (6.0, y_mid)])

    # 支路 2：V2 串 R2
    wire(ax, [(3.5, y_rail), (3.5, y_mid)])
    vsrc(ax, 3.5, y_rail, y_mid, '$V_2 = 6\\,\\mathrm{V}$', label_side='left')
    wire(ax, [(3.5, y_mid), (4.6, y_mid)])
    res_h(ax, y_mid, 4.6, 5.8, '$R_2 = 2\\,\\mathrm{k}\\Omega$')
    wire(ax, [(5.8, y_mid), (6.0, y_mid)])
    dot(ax, 6.0, y_mid)

    # 端口 a
    wire(ax, [(6.0, y_mid), (8.6, y_mid)])
    term(ax, 8.6, y_mid, 'a', dx=0.0, dy=0.40, ha='center')

    # R3 支路（节点 a → 公共端）
    wire(ax, [(7.4, y_mid), (7.4, 2.7)])
    res_v(ax, 7.4, 2.7, 1.7, '$R_3 = 3\\,\\mathrm{k}\\Omega$', side='right')
    wire(ax, [(7.4, 1.7), (7.4, y_rail)])
    dot(ax, 7.4, y_mid)
    dot(ax, 7.4, y_rail)

    # 端口 b
    term(ax, 8.6, y_rail, 'b', dx=0.0, dy=-0.40, ha='center')

    # 虚线框：线性含源二端网络
    ax.add_patch(Rectangle((0.8, 0.30), 7.2, 5.55, fill=False, lw=1.4, ls=(0, (6, 4)),
                           edgecolor='0.45', zorder=1))
    label(ax, 0.9, 6.05, '线性含源二端网络 N', color='0.35')

    ax.set_title('图 2  原含源二端网络（$V_1$=12 V / $R_1$=1 kΩ，$V_2$=6 V / $R_2$=2 kΩ，$R_3$=3 kΩ）',
                 fontsize=TITLE_FS, y=0.99)
    save(fig, 'thevenin_network.jpg')


# --------------------------------------------------------------------------
# 图 3：戴维南等效电路 + 负载
# --------------------------------------------------------------------------
def fig_thevenin_equivalent():
    fig, ax = new_ax(9.2, 5.0, xlim=(-1.6, 9.6), ylim=(-0.6, 5.4))
    y_rail, y_top = 0.8, 3.6

    wire(ax, [(1.6, y_rail), (7.8, y_rail)])
    ground(ax, 2.5, y_rail)

    wire(ax, [(1.6, y_rail), (1.6, y_top)])
    vsrc(ax, 1.6, y_rail, y_top, '$V_{th} = 8.18\\,\\mathrm{V}$', label_side='left')
    wire(ax, [(1.6, y_top), (2.6, y_top)])
    res_h(ax, y_top, 2.6, 4.0, '$R_{th} = 545.45\\,\\Omega$')
    wire(ax, [(4.0, y_top), (6.2, y_top)])
    dot(ax, 6.2, y_top)
    label(ax, 6.2, y_top + 0.42, 'A', ha='center')

    wire(ax, [(6.2, y_top), (7.8, y_top)])
    term(ax, 7.8, y_top, 'a', dx=0.0, dy=0.40, ha='center')

    wire(ax, [(6.2, y_top), (6.2, 2.7)])
    res_v(ax, 6.2, 2.7, 1.7, '$R_L$')
    wire(ax, [(6.2, 1.7), (6.2, y_rail)])
    dot(ax, 6.2, y_rail)
    term(ax, 7.8, y_rail, 'b', dx=0.0, dy=-0.40, ha='center')

    arrow(ax, 7.15, y_rail, 7.15, y_top, style='<->', lw=1.3)
    label(ax, 7.38, 2.4, '$V_L$', fs=FS + 1)
    arrow(ax, 5.70, 3.30, 5.70, 2.50, style='-|>', lw=1.5)
    label(ax, 5.50, 2.90, '$I_L$', ha='right', fs=FS + 1)

    ax.set_title('图 3  戴维南等效电路（$V_{th}$ = 8.18 V，$R_{th}$ = 545.45 Ω）接负载 $R_L$',
                 fontsize=TITLE_FS, y=0.99)
    save(fig, 'thevenin_equivalent.jpg')


# --------------------------------------------------------------------------
# 图 4 / 图 5 公用的共源级拓扑
# --------------------------------------------------------------------------
def _draw_common_source(ax, y_rail=1.1, y_top=6.3, y_gate=2.9, x_mos=6.6, x_g=4.3,
                        x_in=1.0, draw_input=True, draw_bulk=True, rail_right=6.9):
    """题卡那张 NMOS 共源放大电路。draw_input=False 时不画输入/Cb1（直流通路用）。"""
    # 电源轨（从 R_g1 顶部引出到 V_DD）
    wire(ax, [(x_g, y_top), (8.2, y_top)])
    term(ax, 8.2, y_top, '$V_{DD} = 5\\,\\mathrm{V}$', dx=0.26)

    # R_d
    wire(ax, [(x_mos, y_top), (x_mos, 5.5)])
    res_v(ax, x_mos, 5.5, 4.4, '$R_d = 2\\,\\mathrm{k}\\Omega$')
    wire(ax, [(x_mos, 4.4), (x_mos, 3.95)])
    dot(ax, x_mos, 3.95)
    label(ax, x_mos - 0.28, 3.74, 'd', ha='right', fs=FS + 1)
    wire(ax, [(x_mos, 3.95), (8.2, 3.95)])
    term(ax, 8.2, 3.95, '$v_o$', dx=0.26)
    arrow(ax, x_mos + 0.34, 4.36, x_mos + 0.34, 4.00, style='-|>', lw=1.5)
    label(ax, x_mos + 0.52, 4.20, '$i_D$')

    # MOS 管：沟道、栅极板、源极、衬底
    wire(ax, [(x_mos, 3.95), (x_mos, 3.4)])
    wire(ax, [(x_mos, 3.4), (x_mos, 2.4)], lw=LW + 0.6)
    wire(ax, [(x_mos, 2.4), (x_mos, y_rail)])
    wire(ax, [(x_mos - 0.42, 3.28), (x_mos - 0.42, 2.52)], lw=LW + 0.6)
    wire(ax, [(x_g, y_gate), (x_mos - 0.42, y_gate)])
    dot(ax, x_g, y_gate)
    label(ax, x_g - 0.22, y_gate - 0.36, 'g', ha='right', fs=FS + 1)
    label(ax, x_mos - 0.28, 1.42, 's', ha='right', fs=FS + 1)
    if draw_bulk:
        wire(ax, [(x_mos, 2.05), (7.35, 2.05)])
        arrow(ax, 7.10, 2.05, x_mos + 0.10, 2.05, style='-|>', lw=1.5, ms=11)
        term(ax, 7.35, 2.05, 'B', dx=0.0, dy=-0.38, ha='center')

    # R_g1 / R_g2 分压
    wire(ax, [(x_g, y_top), (x_g, 5.5)])
    res_v(ax, x_g, 5.5, 4.4, '$R_{g1} = 60\\,\\mathrm{k}\\Omega$')
    wire(ax, [(x_g, 4.4), (x_g, y_gate)])
    wire(ax, [(x_g, y_gate), (x_g, 2.3)])
    res_v(ax, x_g, 2.3, 1.5, '$R_{g2} = 40\\,\\mathrm{k}\\Omega$')
    wire(ax, [(x_g, 1.5), (x_g, y_rail)])

    # 地
    wire(ax, [(1.6, y_rail), (rail_right, y_rail)])
    ground(ax, 2.7, y_rail)

    if draw_input:
        wire(ax, [(x_in, y_gate), (2.85, y_gate)])
        cap_h(ax, y_gate, 2.85, 3.05)
        wire(ax, [(3.05, y_gate), (x_g, y_gate)])
        label(ax, 2.95, y_gate + 0.58, '$C_{b1}$', ha='center')
        wire(ax, [(x_in, y_rail), (1.6, y_rail)])
        term(ax, x_in, y_gate)
        term(ax, x_in, y_rail)
        arrow(ax, x_in - 0.58, y_rail, x_in - 0.58, y_gate, style='<->', lw=1.3)
        label(ax, x_in - 0.90, 2.0, '$v_i$', ha='center', rot=90, fs=FS + 1)
        label(ax, x_in - 0.38, 2.65, '+', ha='center')
        label(ax, x_in - 0.38, 1.40, '-', ha='center')


def fig_mos_circuit():
    fig, ax = new_ax(9.6, 5.4, xlim=(-1.2, 10.4), ylim=(0.1, 7.0))
    _draw_common_source(ax)
    ax.set_title('图 4  NMOS 共源放大电路（$V_{DD}$=5 V，$R_{g1}$=60 kΩ，$R_{g2}$=40 kΩ，$R_d$=2 kΩ）',
                 fontsize=TITLE_FS, y=0.99)
    save(fig, 'mos_circuit.jpg')


def fig_mos_dc_path():
    fig, ax = new_ax(9.6, 5.9, xlim=(-1.2, 10.4), ylim=(0.1, 7.9))
    _draw_common_source(ax, draw_input=False, draw_bulk=False, rail_right=7.8)

    y_gate = 2.9
    # 直流下 C_b1 开路：只画两块极板，左侧引线用虚线断开
    cap_h(ax, y_gate, 2.85, 3.05, color='0.35')
    wire(ax, [(3.05, y_gate), (4.3, y_gate)])
    wire(ax, [(2.85, y_gate), (2.45, y_gate)], lw=1.4, ls=(0, (4, 3)), color='0.35')
    label(ax, 2.35, y_gate, '输入支路已去掉', ha='right', fs=FS_S, color='0.35')
    label(ax, 2.95, y_gate + 0.62, '$C_{b1}$ 开路', ha='center', color='0.35')

    # V_GS：栅极节点对地（源极）
    arrow(ax, 3.60, 1.10, 3.60, 2.90, style='<->', lw=1.3)
    label(ax, 3.42, 1.95, '$V_{GS} = 2\\,\\mathrm{V}$', ha='right')
    # V_G：栅极节点
    wire(ax, [(2.70, 4.28), (4.24, 2.98)], lw=1.2, ls=(0, (4, 3)), color='0.45')
    label(ax, 2.62, 4.30, '$V_G = 2\\,\\mathrm{V}$', ha='right')
    # I_G = 0
    label(ax, 4.80, 3.30, '$I_G = 0$', fs=FS_S, color='0.35')
    arrow(ax, 5.55, 3.24, 5.55, 2.98, style='-|>', lw=1.2, ms=10)
    # V_DS：漏极节点对地
    arrow(ax, 7.45, 1.10, 7.45, 3.95, style='<->', lw=1.3)
    label(ax, 7.68, 2.50, '$V_{DS} = 4.1339\\,\\mathrm{V}$', rot=90)

    label(ax, 1.55, 7.78,
          '直流分析：$C_{b1}$ 开路、栅极电流 $I_G = 0$\n'
          '$V_G = V_{GS} = 2\\,\\mathrm{V}$，$I_D = 0.4331\\,\\mathrm{mA}$，$V_{DS} = 4.1339\\,\\mathrm{V}$（饱和区）',
          va='top', fs=FS_S, box=BOX)

    ax.set_title('图 5  直流通路（$C_{b1}$ 开路，栅极电流为 0）', fontsize=TITLE_FS, y=0.99)
    save(fig, 'mos_dc_path.jpg')


def fig_mos_small_signal():
    fig, ax = new_ax(9.8, 5.4, xlim=(-0.6, 10.4), ylim=(0.2, 7.6))
    y_rail, y_drain = 1.0, 3.9

    wire(ax, [(1.35, y_rail), (7.8, y_rail)])
    ground(ax, 3.3, y_rail)

    # 栅极节点 + R_g
    wire(ax, [(1.35, 4.4), (2.6, 4.4)])
    dot(ax, 2.6, 4.4)
    label(ax, 2.6, 4.64, 'g', ha='center', fs=FS + 1)
    wire(ax, [(2.6, 4.4), (2.6, 3.5)])
    res_v(ax, 2.6, 3.5, 2.5, None)
    wire(ax, [(2.6, 2.5), (2.6, y_rail)])
    label(ax, 2.34, 3.0, '$R_g$', ha='right')
    dot(ax, 2.6, y_rail)

    # v_gs
    arrow(ax, 1.35, y_rail, 1.35, 4.4, style='<->', lw=1.3)
    label(ax, 1.05, 2.7, '$v_{gs}$', ha='center', rot=90, fs=FS + 1)
    label(ax, 1.57, 3.95, '+', ha='center')
    label(ax, 1.57, 1.45, '-', ha='center')

    # 受控电流源 g_m·v_gs（漏 → 源）
    wire(ax, [(4.0, y_drain), (4.0, 3.15)])
    ax.add_patch(Circle((4.0, 2.6), 0.55, facecolor='white', edgecolor='black', lw=LW, zorder=5))
    arrow(ax, 4.0, 2.85, 4.0, 2.35, style='-|>', lw=1.6, ms=12)
    wire(ax, [(4.0, 2.05), (4.0, y_rail)])
    label(ax, 4.74, 2.6, '$g_m\\,v_{gs}$')
    dot(ax, 4.0, y_rail)

    # 漏极节点
    wire(ax, [(4.0, y_drain), (9.0, y_drain)])
    label(ax, 5.3, y_drain + 0.24, 'd', ha='center', fs=FS + 1)
    label(ax, 5.8, y_rail - 0.28, 's', ha='center', fs=FS + 1)

    # r_o
    wire(ax, [(6.6, y_drain), (6.6, 3.3)])
    res_v(ax, 6.6, 3.3, 2.3, '$r_o$')
    wire(ax, [(6.6, 2.3), (6.6, y_rail)])
    dot(ax, 6.6, y_drain)
    dot(ax, 6.6, y_rail)

    # R_d
    wire(ax, [(7.8, y_drain), (7.8, 3.3)])
    res_v(ax, 7.8, 3.3, 2.3, None)
    wire(ax, [(7.8, 2.3), (7.8, y_rail)])
    label(ax, 8.14, 3.5, '$R_d$')
    dot(ax, 7.8, y_drain)
    dot(ax, 7.8, y_rail)

    term(ax, 9.0, y_drain, '$v_o$', dx=0.26)

    label(ax, 1.05, 7.45,
          '中频小信号模型（$C_{b1}$ 短路、$V_{DD}$ 与地同电位）\n'
          '$R_g = R_{g1} \\parallel R_{g2} = 24\\,\\mathrm{k}\\Omega$，'
          '$r_o = 115.45\\,\\mathrm{k}\\Omega$，$g_m = 0.866\\,\\mathrm{mS}$\n'
          '$A_v = -g_m\\,(R_d \\parallel r_o) = -1.70$',
          va='top', fs=FS_S, box=BOX)

    ax.set_title('图 6  小信号等效模型（受控源 $g_m v_{gs}$ 与 $r_o$ 并联，负载 $R_d$）',
                 fontsize=TITLE_FS, y=0.99)
    save(fig, 'mos_small_signal.jpg')


if __name__ == '__main__':
    fig_rc_circuit()
    fig_thevenin_network()
    fig_thevenin_equivalent()
    fig_mos_circuit()
    fig_mos_dc_path()
    fig_mos_small_signal()
