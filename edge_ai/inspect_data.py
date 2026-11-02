#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第 1 步：数据体检 —— 验证「物理一致性」前提
=================================================
目的：用真实数据确认多传感器之间是否存在物理关系，
      为第 2 步「物理一致性建模」提供依据。

运行环境：虚拟机 Ubuntu（rknn venv）
依赖：    pip install numpy matplotlib
前提：    同级目录有 train_data.csv（RK3566 上 export_data.py 导出）

产出（保存到当前目录）：
    scatter_pairs.png   散点图（看相关性形状：带状=强 / 云团=弱）
    timeseries.png      时间序列图（看同步性与滞后）
    lag_wt_temp.png     水温-气温 滞后相关系数曲线（看滞后量）
控制台打印：
    各传感器对的 Pearson 相关系数 + 水温对气温的最佳滞后步数
"""

import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')   # 无界面环境，只保存图片不弹窗
import matplotlib.pyplot as plt

# ============ 1. 读取数据 ============
ts, temp, hum, press, tds, wt = [], [], [], [], [], []
with open('train_data.csv') as f:
    reader = csv.reader(f)
    next(reader)   # 跳过表头 ts,temp,hum,press,tds,wt
    for row in reader:
        ts.append(row[0])
        temp.append(float(row[1]))
        hum.append(float(row[2]))
        press.append(float(row[3]))
        tds.append(float(row[4]))
        wt.append(float(row[5]))

temp = np.array(temp); hum = np.array(hum)
press = np.array(press); tds = np.array(tds); wt = np.array(wt)
n = len(temp)
print(f"数据条数: {n}")
if n < 50:
    print("⚠️  数据太少（<50 条），先让浮标多跑一会再导。")
    raise SystemExit

# ============ 2. Pearson 相关系数 ============
def r(x, y):
    return np.corrcoef(x, y)[0, 1]

print("\n===== Pearson 相关系数（|r|>0.7 强 / 0.4~0.7 中 / <0.4 弱）=====")
pairs = [
    ('气温-水温 (temp-wt)',   temp, wt),
    ('水温-TDS  (wt-tds)',    wt,   tds),
    ('湿度-气压 (hum-press)', hum,  press),
    ('气温-湿度 (temp-hum)',  temp, hum),   # 附加参考
]
for name, x, y in pairs:
    print(f"  {name:24s} r = {r(x, y):+.3f}")

# ============ 3. 散点图（两两传感器）============
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
axes = axes.ravel()
scatter_pairs = [
    ('AIR TEMP -> WATER TEMP', temp, wt, 'AIR TEMP (C)', 'WATER TEMP (C)'),
    ('WATER TEMP -> TDS',       wt,   tds, 'WATER TEMP (C)', 'TDS (ppm)'),
    ('HUMIDITY -> PRESSURE',    hum,  press, 'HUMIDITY (%)', 'PRESSURE (hPa)'),
    ('AIR TEMP -> HUMIDITY',    temp, hum, 'AIR TEMP (C)', 'HUMIDITY (%)'),
]
for ax, (title, x, y, xl, yl) in zip(axes, scatter_pairs):
    ax.scatter(x, y, s=6, alpha=0.4, color='#22d3ee', edgecolors='none')
    ax.set_title(f'{title}   r={r(x, y):+.3f}', fontsize=11)
    ax.set_xlabel(xl); ax.set_ylabel(yl)
    ax.grid(alpha=0.3)
fig.suptitle('Scatter: physical relation between sensor pairs', fontsize=13)
fig.tight_layout()
fig.savefig('scatter_pairs.png', dpi=110)
print("\n已保存 scatter_pairs.png")

# ============ 4. 时间序列图（看同步性与滞后）============
# 只画最近 N 条，避免太挤
N = min(n, 3000)
idx = np.arange(N)
fig, ax = plt.subplots(figsize=(14, 6))
# 各传感器归一化到 0~1，才能叠在一张图比较涨跌趋势
def norm(a):
    return (a[-N:] - a[-N:].min()) / (a[-N:].max() - a[-N:].min() + 1e-9)

ax.plot(idx, norm(temp), label='AIR TEMP',   color='#22d3ee', lw=1)
ax.plot(idx, norm(wt),   label='WATER TEMP', color='#4ade80', lw=1)
ax.plot(idx, norm(hum),  label='HUMIDITY',   color='#a78bfa', lw=1)
ax.plot(idx, norm(press),label='PRESSURE',   color='#fbbf24', lw=1)
ax.plot(idx, norm(tds),  label='TDS',        color='#f472b6', lw=1)
ax.set_title(f'Normalized time series (last {N} points)', fontsize=12)
ax.set_xlabel('sample index'); ax.set_ylabel('normalized')
ax.legend(loc='upper right', ncol=5, fontsize=9)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig('timeseries.png', dpi=110)
print("已保存 timeseries.png")

# ============ 5. 滞后分析（水温 vs 气温）============
# 水温有热惯性，滞后于气温。算「气温提前 k 步」时与水温的相关系数，
# 找相关系数最大的 k，就是水温滞后气温的步数。
MAX_LAG = 300   # 最多 300 步（约 10 分钟，按 2s 采样间隔估算）
corrs = []
for lag in range(0, MAX_LAG + 1):
    if lag == 0:
        c = r(temp, wt)
    else:
        c = r(temp[:-lag], wt[lag:])   # 气温提前 lag 步，与水温对齐
    corrs.append(c)
corrs = np.array(corrs)
best = int(np.argmax(corrs))
print(f"\n===== 水温滞后气温分析 =====")
print(f"  滞后 0 步相关系数: {corrs[0]:+.3f}")
print(f"  最佳滞后 {best} 步，相关系数 {corrs[best]:+.3f}")

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(range(MAX_LAG + 1), corrs, color='#22d3ee', lw=2)
ax.axvline(best, color='#f87171', ls='--', lw=1)
ax.set_title(f'Lag correlation: AIR TEMP vs WATER TEMP (best lag = {best})')
ax.set_xlabel('lag (samples)'); ax.set_ylabel('Pearson r')
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig('lag_wt_temp.png', dpi=110)
print("已保存 lag_wt_temp.png")
print("\n体检完成。看三张图，对照判据下结论。")
