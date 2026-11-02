#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第 3 步：残差计算
=================================================
目标：残差 = 实际值 - 物理预期值，剥离物理真值，得到「纯净异常信号」。

残差里剩下的成分：噪声（小随机）+ 漂移（慢）+ 异常（快）。

运行环境：虚拟机 Ubuntu（系统 python3）
依赖：    numpy matplotlib（已装）
前提：    同级目录有 train_data.csv 和 physical_model.json

产出：
    residual_series.png   残差时间序列图（看是否贴 0 轴、有无异常尖峰）
    residual_hist.png     残差直方图（看是否近似正态=钟形）
    residual_stats.json   残差均值/标准差（第 4 步定阈值要用）
"""

import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ============ 1. 读数据 ============
temp, hum, wt = [], [], []
with open('train_data.csv') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        temp.append(float(row[1]))
        hum.append(float(row[2]))
        wt.append(float(row[5]))
temp = np.array(temp); hum = np.array(hum); wt = np.array(wt)

# ============ 2. 读物理模型 ============
with open('physical_model.json') as f:
    model = json.load(f)
a1, b1 = model['hum']['a'], model['hum']['b']   # 湿度 = a1*temp + b1
a2, b2 = model['wt']['a'],  model['wt']['b']    # 水温 = a2*temp + b2

# ============ 3. 计算残差（核心一步）============
hum_pred = a1 * temp + b1      # 湿度「物理预期值」
wt_pred  = a2 * temp + b2      # 水温「物理预期值」
hum_res = hum - hum_pred       # 湿度残差 = 实际 - 预期
wt_res  = wt  - wt_pred        # 水温残差

# ============ 4. 统计特征（均值应≈0，标准差供第4步定阈值）============
hum_mean, hum_std = float(hum_res.mean()), float(hum_res.std())
wt_mean,  wt_std  = float(wt_res.mean()),  float(wt_res.std())

print("===== 残差统计特征 =====")
print(f"  湿度残差: 均值 {hum_mean:+.4f}  标准差 {hum_std:.4f}")
print(f"  水温残差: 均值 {wt_mean:+.4f}  标准差 {wt_std:.4f}")
print("  (均值应≈0；标准差是第4步定阈值的基础，如 3σ 阈值 = 3×标准差)")

# ============ 5. 画残差时间序列 ============
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
idx = np.arange(len(hum_res))

axes[0].plot(idx, hum_res, color='#22d3ee', lw=0.8)
axes[0].axhline(0, color='#f87171', ls='--', lw=1)
axes[0].axhline(hum_std, color='#5b7a94', ls=':', lw=1, label='±1σ')
axes[0].axhline(-hum_std, color='#5b7a94', ls=':', lw=1)
axes[0].set_title(f'HUMIDITY residual (std={hum_std:.3f})')
axes[0].set_ylabel('residual (%)')
axes[0].legend(); axes[0].grid(alpha=0.3)

axes[1].plot(idx, wt_res, color='#4ade80', lw=0.8)
axes[1].axhline(0, color='#f87171', ls='--', lw=1)
axes[1].axhline(wt_std, color='#5b7a94', ls=':', lw=1, label='±1σ')
axes[1].axhline(-wt_std, color='#5b7a94', ls=':', lw=1)
axes[1].set_title(f'WATER TEMP residual (std={wt_std:.3f})')
axes[1].set_xlabel('sample index'); axes[1].set_ylabel('residual (C)')
axes[1].legend(); axes[1].grid(alpha=0.3)

fig.suptitle('Residual time series (should hug 0, spikes = anomalies)', fontsize=13)
fig.tight_layout()
fig.savefig('residual_series.png', dpi=110)
print("已保存 residual_series.png")

# ============ 6. 画残差直方图（看是否正态=钟形）============
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].hist(hum_res, bins=60, color='#22d3ee', alpha=0.7, edgecolor='none')
axes[0].axvline(hum_mean, color='#f87171', ls='--', lw=1)
axes[0].set_title(f'HUMIDITY residual histogram (mean={hum_mean:+.3f}, std={hum_std:.3f})')
axes[0].set_xlabel('residual (%)'); axes[0].set_ylabel('count')

axes[1].hist(wt_res, bins=60, color='#4ade80', alpha=0.7, edgecolor='none')
axes[1].axvline(wt_mean, color='#f87171', ls='--', lw=1)
axes[1].set_title(f'WATER TEMP residual histogram (mean={wt_mean:+.3f}, std={wt_std:.3f})')
axes[1].set_xlabel('residual (C)'); axes[1].set_ylabel('count')

fig.suptitle('Residual distribution (bell-shaped = physical truth stripped clean)', fontsize=13)
fig.tight_layout()
fig.savefig('residual_hist.png', dpi=110)
print("已保存 residual_hist.png")

# ============ 7. 保存统计特征（第 4 步用）============
stats = {
    'hum_residual': {'mean': hum_mean, 'std': hum_std},
    'wt_residual':  {'mean': wt_mean,  'std': wt_std},
}
with open('residual_stats.json', 'w') as f:
    json.dump(stats, f, indent=2)
print("已保存 residual_stats.json")
print("\n第 3 步完成。看残差时间序列有没有可疑尖峰、直方图是不是钟形。")
