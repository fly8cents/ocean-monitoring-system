#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第 2 步：物理一致性建模（线性回归）
=================================================
目标：建立「物理预期值」模型，用气温预测湿度/水温的「物理应该值」，
      供第 3 步计算残差（实际值 - 物理预期值）使用。

用到的物理关系（来自第 1 步体检）：
    湿度 = a1 * 气温 + b1   （热力学，r=-0.805）
    水温 = a2 * 气温 + b2   （传热，   r=+0.753）

运行环境：虚拟机 Ubuntu（系统 python3 即可）
依赖：    numpy matplotlib（第 1 步已装）
前提：    同级目录有 train_data.csv

产出：
    physical_model.json   斜率/截距/R²（第 3 步 + 板端部署都要用）
    scatter_fit.png       散点图 + 拟合直线（可视化验证拟合效果）
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
    next(reader)   # 跳过表头
    for row in reader:
        temp.append(float(row[1]))   # 气温
        hum.append(float(row[2]))    # 湿度
        wt.append(float(row[5]))     # 水温
temp = np.array(temp); hum = np.array(hum); wt = np.array(wt)

# ============ 2. 最小二乘拟合 + R² ============
def fit_linear(x, y):
    """拟合 y = a*x + b，返回 (a, b, R²)。"""
    a, b = np.polyfit(x, y, 1)          # 最小二乘一次多项式拟合
    y_pred = a * x + b                  # 预测值
    ss_res = np.sum((y - y_pred) ** 2)  # 残差平方和
    ss_tot = np.sum((y - y.mean()) ** 2)  # 总平方和
    r2 = 1 - ss_res / ss_tot            # 决定系数：1=完美，0=没解释力
    return a, b, r2

# ============ 3. 拟合两条物理关系 ============
a1, b1, r2_1 = fit_linear(temp, hum)   # 湿度 = a1*气温 + b1
a2, b2, r2_2 = fit_linear(temp, wt)    # 水温 = a2*气温 + b2

print("===== 物理一致性模型（线性回归）=====")
print(f"  湿度 = {a1:+.4f} * 气温 {b1:+.4f}   R² = {r2_1:.4f}")
print(f"  水温 = {a2:+.4f} * 气温 {b2:+.4f}   R² = {r2_2:.4f}")
print("  (R² 越接近 1 线性关系越强；>0.5 可用，<0.3 这条关系别用)")

# ============ 4. 画散点图 + 拟合直线 ============
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# 左：湿度 vs 气温
axes[0].scatter(temp, hum, s=6, alpha=0.4, color='#22d3ee', edgecolors='none')
xs = np.linspace(temp.min(), temp.max(), 100)
axes[0].plot(xs, a1 * xs + b1, color='#f87171', lw=2,
             label=f'fit: hum = {a1:+.3f}*temp {b1:+.3f}')
axes[0].set_title(f'HUMIDITY vs AIR TEMP   R²={r2_1:.3f}')
axes[0].set_xlabel('AIR TEMP (C)'); axes[0].set_ylabel('HUMIDITY (%)')
axes[0].legend(); axes[0].grid(alpha=0.3)

# 右：水温 vs 气温
axes[1].scatter(temp, wt, s=6, alpha=0.4, color='#4ade80', edgecolors='none')
axes[1].plot(xs, a2 * xs + b2, color='#f87171', lw=2,
             label=f'fit: wt = {a2:+.3f}*temp {b2:+.3f}')
axes[1].set_title(f'WATER TEMP vs AIR TEMP   R²={r2_2:.3f}')
axes[1].set_xlabel('AIR TEMP (C)'); axes[1].set_ylabel('WATER TEMP (C)')
axes[1].legend(); axes[1].grid(alpha=0.3)

fig.suptitle('Physical Consistency Model (linear fit)', fontsize=13)
fig.tight_layout()
fig.savefig('scatter_fit.png', dpi=110)
print("已保存 scatter_fit.png")

# ============ 5. 保存模型参数（供第 3 步 + 板端部署用）============
model = {
    'hum': {'input': 'temp', 'a': float(a1), 'b': float(b1), 'r2': float(r2_1)},
    'wt':  {'input': 'temp', 'a': float(a2), 'b': float(b2), 'r2': float(r2_2)},
}
with open('physical_model.json', 'w') as f:
    json.dump(model, f, indent=2)
print("已保存 physical_model.json")
print("\n第 2 步完成。看 R² 和散点图，判断线性拟合够不够用。")
