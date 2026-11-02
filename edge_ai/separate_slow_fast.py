#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第 4 步：快慢分离（漂移 vs 异常）
=================================================
目标：把残差拆成「慢变成分（漂移）」和「快变成分（异常）」，
      分别供第 5 步判「传感器漂移」和「异常报警」。

方法：滑动平均（低通滤波）
    慢变 = 滑动平均(残差)        ← 抹平快变和噪声，只留慢趋势
    快变 = 残差 - 慢变           ← 减掉慢趋势，剩下的就是快变（异常尖峰）

运行环境：虚拟机 Ubuntu（系统 python3）
依赖：    numpy matplotlib（已装）
前提：    同级目录有 train_data.csv 和 physical_model.json

产出：
    slow_fast.png     慢变分离图（原始残差 + 漂移曲线）
    fast_component.png 快变成分图（提纯后的异常尖峰）
    fast_stats.json   快变成分标准差（第 5 步定异常阈值用）
"""

import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ============ 1. 读数据 + 物理模型 + 计算残差 ============
temp, hum, wt = [], [], []
with open('train_data.csv') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        temp.append(float(row[1])); hum.append(float(row[2])); wt.append(float(row[5]))
temp = np.array(temp); hum = np.array(hum); wt = np.array(wt)

with open('physical_model.json') as f:
    model = json.load(f)
a1, b1 = model['hum']['a'], model['hum']['b']
a2, b2 = model['wt']['a'],  model['wt']['b']

hum_res = hum - (a1 * temp + b1)   # 湿度残差
wt_res  = wt  - (a2 * temp + b2)   # 水温残差

# ============ 2. 滑动平均（低通滤波）============
WINDOW = 100   # 窗口 ~3 分钟（按 2s 采样）。窗口大=更平滑但可能吞异常，小=漂移提取不干净
kernel = np.ones(WINDOW) / WINDOW

def smooth(x):
    """滑动平均，提取慢变成分（漂移趋势）。"""
    return np.convolve(x, kernel, mode='same')

hum_slow = smooth(hum_res)   # 湿度漂移（慢变）
wt_slow  = smooth(wt_res)    # 水温漂移（慢变）
hum_fast = hum_res - hum_slow   # 湿度异常（快变）
wt_fast  = wt_res  - wt_slow    # 水温异常（快变）

# ============ 3. 统计快变成分（异常信号）============
hum_fast_std = float(hum_fast.std())
wt_fast_std  = float(wt_fast.std())
print("===== 快慢分离结果 =====")
print(f"  湿度漂移范围: {hum_slow.min():+.3f} ~ {hum_slow.max():+.3f}")
print(f"  水温漂移范围: {wt_slow.min():+.3f} ~ {wt_slow.max():+.3f}")
print(f"  湿度快变(异常)标准差: {hum_fast_std:.4f}")
print(f"  水温快变(异常)标准差: {wt_fast_std:.4f}")
print("  (漂移范围≈0 = 传感器无漂移；快变标准差是第5步异常阈值的基础)")

# ============ 4. 画慢变分离图 ============
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
idx = np.arange(len(hum_res))

axes[0].plot(idx, hum_res, color='#22d3ee', lw=0.6, alpha=0.5, label='raw residual')
axes[0].plot(idx, hum_slow, color='#f87171', lw=2, label='slow (drift)')
axes[0].axhline(0, color='#5b7a94', ls='--', lw=1)
axes[0].set_title('HUMIDITY: raw residual vs slow drift')
axes[0].set_ylabel('residual (%)'); axes[0].legend(); axes[0].grid(alpha=0.3)

axes[1].plot(idx, wt_res, color='#4ade80', lw=0.6, alpha=0.5, label='raw residual')
axes[1].plot(idx, wt_slow, color='#f87171', lw=2, label='slow (drift)')
axes[1].axhline(0, color='#5b7a94', ls='--', lw=1)
axes[1].set_title('WATER TEMP: raw residual vs slow drift')
axes[1].set_xlabel('sample index'); axes[1].set_ylabel('residual (C)')
axes[1].legend(); axes[1].grid(alpha=0.3)

fig.suptitle('Slow-fast separation (red line = drift trend)', fontsize=13)
fig.tight_layout()
fig.savefig('slow_fast.png', dpi=110)
print("已保存 slow_fast.png")

# ============ 5. 画快变成分图 ============
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

axes[0].plot(idx, hum_fast, color='#22d3ee', lw=0.8)
axes[0].axhline(0, color='#f87171', ls='--', lw=1)
axes[0].axhline(hum_fast_std, color='#5b7a94', ls=':', lw=1, label='±1σ')
axes[0].axhline(-hum_fast_std, color='#5b7a94', ls=':', lw=1)
axes[0].set_title(f'HUMIDITY: fast component (anomaly signal, std={hum_fast_std:.3f})')
axes[0].set_ylabel('fast (%)'); axes[0].legend(); axes[0].grid(alpha=0.3)

axes[1].plot(idx, wt_fast, color='#4ade80', lw=0.8)
axes[1].axhline(0, color='#f87171', ls='--', lw=1)
axes[1].axhline(wt_fast_std, color='#5b7a94', ls=':', lw=1, label='±1σ')
axes[1].axhline(-wt_fast_std, color='#5b7a94', ls=':', lw=1)
axes[1].set_title(f'WATER TEMP: fast component (anomaly signal, std={wt_fast_std:.3f})')
axes[1].set_xlabel('sample index'); axes[1].set_ylabel('fast (C)')
axes[1].legend(); axes[1].grid(alpha=0.3)

fig.suptitle('Fast component (spikes = anomalies)', fontsize=13)
fig.tight_layout()
fig.savefig('fast_component.png', dpi=110)
print("已保存 fast_component.png")

# ============ 6. 保存快变统计（第 5 步用）============
fast_stats = {
    'hum_fast': {'std': hum_fast_std},
    'wt_fast':  {'std': wt_fast_std},
}
with open('fast_stats.json', 'w') as f:
    json.dump(fast_stats, f, indent=2)
print("已保存 fast_stats.json")
print("\n第 4 步完成。看 slow_fast.png（红线漂移趋势）+ fast_component.png（提纯尖峰）。")
