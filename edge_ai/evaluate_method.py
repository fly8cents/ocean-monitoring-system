#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第 6 步（一）：合成数据验证 —— 定量评估 A+B 方法
=================================================
思路：取一段干净的正常数据作为「基线」，人为注入已知的异常和漂移，
      因为注入位置/幅度是我们定的，就有「标准答案」，能算检出率。

评估指标：Precision（精确率）、Recall（召回率）、F1。

运行环境：虚拟机 Ubuntu（系统 python3）
依赖：    numpy matplotlib（已装）
前提：    同级目录有 train_data.csv

产出：
    eval_anomaly.png   注入的异常 vs 检出的异常 对比
    eval_drift.png     慢变成分 vs 注入的漂移 对比
"""

import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ============ 1. 读数据，取前 1000 条作为「干净基线」============
temp, hum, wt = [], [], []
with open('train_data.csv') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        temp.append(float(row[1])); hum.append(float(row[2])); wt.append(float(row[5]))
temp = np.array(temp); hum = np.array(hum); wt = np.array(wt)

N = 1000                      # 基线长度
temp = temp[:N]; hum = hum[:N]; wt = wt[:N]

# ============ 2. 用基线拟合物理模型（模拟「训练阶段」）============
def fit_linear(x, y):
    a, b = np.polyfit(x, y, 1)
    return a, b
a1, b1 = fit_linear(temp, hum)   # 湿度 = a1*temp + b1
a2, b2 = fit_linear(temp, wt)    # 水温 = a2*temp + b2

# ============ 3. 注入已知异常 + 漂移（模拟「部署后遇到异常」）============
hum_mod = hum.copy()
wt_mod  = wt.copy()

# 注入异常①：湿度 点 300~330 加 +3%（模拟突变异常）
hum_mod[300:330] += 3.0
# 注入异常②：水温 点 600~630 加 +0.5℃（模拟突变异常）
wt_mod[600:630] += 0.5
# 注入漂移：水温 点 800~999 加线性 0→+0.5℃（模拟传感器老化漂移）
drift = np.linspace(0, 0.5, 200)
wt_mod[800:1000] += drift

# 标准答案（ground truth）
hum_gt = np.zeros(N, dtype=bool); hum_gt[300:330] = True
wt_gt  = np.zeros(N, dtype=bool); wt_gt[600:630]  = True

# ============ 4. 跑 A+B 方法（残差 → 快慢分离 → 3σ 判定）============
hum_res = hum_mod - (a1 * temp + b1)
wt_res  = wt_mod  - (a2 * temp + b2)

WINDOW = 100
kernel = np.ones(WINDOW) / WINDOW
def smooth(x):
    return np.convolve(x, kernel, mode='same')

hum_slow = smooth(hum_res); wt_slow = smooth(wt_res)
hum_fast = hum_res - hum_slow; wt_fast = wt_res - wt_slow

SIGMA = 3.0
hum_th = SIGMA * hum_fast.std(); wt_th = SIGMA * wt_fast.std()
hum_detected = np.abs(hum_fast) > hum_th   # 检出的异常点（布尔）
wt_detected  = np.abs(wt_fast)  > wt_th

# ============ 5. 计算 Precision / Recall / F1 ============
def metrics(detected, ground_truth):
    tp = int(np.sum(detected & ground_truth))
    fp = int(np.sum(detected & ~ground_truth))
    fn = int(np.sum(~detected & ground_truth))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return tp, fp, fn, precision, recall, f1

hum_m = metrics(hum_detected, hum_gt)
wt_m  = metrics(wt_detected,  wt_gt)

print("===== 合成数据验证结果（3σ 阈值）=====")
print(f"  湿度异常: TP={hum_m[0]} FP={hum_m[1]} FN={hum_m[2]}  "
      f"Precision={hum_m[3]:.3f} Recall={hum_m[4]:.3f} F1={hum_m[5]:.3f}")
print(f"  水温异常: TP={wt_m[0]} FP={wt_m[1]} FN={wt_m[2]}  "
      f"Precision={wt_m[3]:.3f} Recall={wt_m[4]:.3f} F1={wt_m[5]:.3f}")
print("  (Recall=1 表示注入的异常全被检出；Precision 高表示误报少)")

# ============ 6. 画图：注入异常 vs 检出异常 ============
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
idx = np.arange(N)

axes[0].plot(idx, hum_fast, color='#22d3ee', lw=0.8, label='fast component')
axes[0].axhline(hum_th, color='#fbbf24', ls='--', lw=1, label='±3σ')
axes[0].axhline(-hum_th, color='#fbbf24', ls='--', lw=1)
axes[0].axvspan(300, 330, color='#4ade80', alpha=0.15, label='injected anomaly')
# 检出的点标红
axes[0].scatter(idx[hum_detected], hum_fast[hum_detected], color='#f87171', s=14, zorder=3, label='detected')
axes[0].set_title(f'HUMIDITY: injected vs detected (Precision={hum_m[3]:.2f}, Recall={hum_m[4]:.2f})')
axes[0].set_ylabel('fast (%)'); axes[0].legend(loc='upper right', fontsize=8); axes[0].grid(alpha=0.3)

axes[1].plot(idx, wt_fast, color='#4ade80', lw=0.8, label='fast component')
axes[1].axhline(wt_th, color='#fbbf24', ls='--', lw=1, label='±3σ')
axes[1].axhline(-wt_th, color='#fbbf24', ls='--', lw=1)
axes[1].axvspan(600, 630, color='#4ade80', alpha=0.15, label='injected anomaly')
axes[1].scatter(idx[wt_detected], wt_fast[wt_detected], color='#f87171', s=14, zorder=3, label='detected')
axes[1].set_title(f'WATER TEMP: injected vs detected (Precision={wt_m[3]:.2f}, Recall={wt_m[4]:.2f})')
axes[1].set_xlabel('sample index'); axes[1].set_ylabel('fast (C)')
axes[1].legend(loc='upper right', fontsize=8); axes[1].grid(alpha=0.3)

fig.suptitle('Synthetic evaluation: injected anomaly (green band) vs detected (red dots)', fontsize=13)
fig.tight_layout()
fig.savefig('eval_anomaly.png', dpi=110)
print("已保存 eval_anomaly.png")

# ============ 7. 画图：慢变成分 vs 注入的漂移 ============
fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(idx, wt_slow, color='#4ade80', lw=1.5, label='slow component (extracted)')
ax.axvspan(800, 1000, color='#fbbf24', alpha=0.12, label='injected drift region')
ax.plot(idx[800:1000], wt_slow[800:1000], color='#f87171', lw=1, label='slow during drift')
ax.axhline(0, color='#5b7a94', ls='--', lw=1)
ax.set_title('WATER TEMP: extracted slow drift vs injected drift (injected 0→+0.5℃ over idx 800~1000)')
ax.set_xlabel('sample index'); ax.set_ylabel('slow (C)')
ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig('eval_drift.png', dpi=110)
print("已保存 eval_drift.png")
print("\n验证完成。看 Recall 是否接近 1、慢变成分是否跟注入漂移吻合。")
