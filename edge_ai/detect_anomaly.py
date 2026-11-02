#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第 5 步：异常判定 + 漂移检测
=================================================
目标：给快变成分定 3σ 阈值，自动挑出异常点（合并成异常事件）；
      给慢变成分做漂移检测（持续偏离 = 漂移）。

这是 A+B 核心算法的最后一步，完成后就得到「报警清单」。

运行环境：虚拟机 Ubuntu（系统 python3）
依赖：    numpy matplotlib（已装）
前提：    同级目录有 train_data.csv 和 physical_model.json

产出：
    anomaly_events.png   快变成分 + 阈值线 + 异常点（红点标记）
    anomaly_events.json  异常事件清单（起止时间、持续、峰值）
"""

import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ============ 1. 读数据（含时间戳）+ 物理模型 ============
ts, temp, hum, wt = [], [], [], []
with open('train_data.csv') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        ts.append(row[0]); temp.append(float(row[1])); hum.append(float(row[2])); wt.append(float(row[5]))
ts = np.array(ts); temp = np.array(temp); hum = np.array(hum); wt = np.array(wt)

with open('physical_model.json') as f:
    model = json.load(f)
a1, b1 = model['hum']['a'], model['hum']['b']
a2, b2 = model['wt']['a'],  model['wt']['b']

# ============ 2. 残差 + 快慢分离 ============
hum_res = hum - (a1 * temp + b1)
wt_res  = wt  - (a2 * temp + b2)

WINDOW = 100
kernel = np.ones(WINDOW) / WINDOW
def smooth(x):
    return np.convolve(x, kernel, mode='same')

hum_slow = smooth(hum_res); wt_slow = smooth(wt_res)
hum_fast = hum_res - hum_slow; wt_fast = wt_res - wt_slow

# ============ 3. 3σ 阈值 + 挑异常点 ============
SIGMA = 3.0   # 3σ 阈值（可调：松=5，紧=2）
hum_th = SIGMA * hum_fast.std(); wt_th = SIGMA * wt_fast.std()

def parse_ts(s):
    """'2026-10-30 21:29:52' -> epoch 秒（用于判断时间连续性）"""
    from datetime import datetime
    return datetime.strptime(s, '%Y-%m-%d %H:%M:%S').timestamp()

def find_events(fast, threshold, ts, max_gap_sec=10.0):
    """把 |fast|>threshold 的连续点合并成「异常事件」，
    但按时间戳连续性分割：相邻异常点间隔超过 max_gap_sec 时事件断开
    （修复：数据有缺口时，缺口两侧的异常不该被粘成一个事件）。
    返回事件列表，每个事件：{start_idx, end_idx, start_ts, end_ts, duration_points, peak}"""
    mask = np.abs(fast) > threshold
    ts_epoch = np.array([parse_ts(t) for t in ts])
    events = []
    i = 0
    n = len(mask)
    while i < n:
        if mask[i]:
            j = i + 1
            # 连续异常点 && 时间间隔不超过 max_gap_sec 才并入当前事件
            while j < n and mask[j] and (ts_epoch[j] - ts_epoch[j-1]) <= max_gap_sec:
                j += 1
            seg = fast[i:j]
            peak = seg[np.argmax(np.abs(seg))]   # 段内峰值（带符号）
            events.append({
                'start_idx': i, 'end_idx': j - 1,
                'start_ts': ts[i], 'end_ts': ts[j-1],
                'duration_points': j - i,
                'peak': round(float(peak), 4),
            })
            i = j
        else:
            i += 1
    return events

hum_events = find_events(hum_fast, hum_th, ts)
wt_events  = find_events(wt_fast,  wt_th,  ts)

print("===== 异常检测结果（3σ 阈值）=====")
print(f"  湿度阈值: ±{hum_th:.4f}%   检出异常事件 {len(hum_events)} 个")
for e in hum_events[:20]:
    print(f"    [{e['start_ts']} ~ {e['end_ts']}] 持续 {e['duration_points']} 点, 峰值 {e['peak']:+.3f}")
print(f"  水温阈值: ±{wt_th:.4f}℃   检出异常事件 {len(wt_events)} 个")
for e in wt_events[:20]:
    print(f"    [{e['start_ts']} ~ {e['end_ts']}] 持续 {e['duration_points']} 点, 峰值 {e['peak']:+.3f}")

# ============ 4. 漂移检测（慢变持续偏离）============
# 判据：慢变的最大绝对偏离 + 净变化（首尾差）
def drift_report(slow, name, unit):
    max_abs = float(np.max(np.abs(slow)))
    net = float(slow[-1] - slow[0])   # 首尾净变化（正的=往上漂，负的=往下漂）
    print(f"  {name}: 最大偏离 {max_abs:+.3f}{unit}, 首尾净变化 {net:+.3f}{unit}")
    return max_abs, net

print("\n===== 漂移检测结果（慢变趋势）=====")
hum_drift_max, hum_drift_net = drift_report(hum_slow, '湿度', '%')
wt_drift_max,  wt_drift_net  = drift_report(wt_slow,  '水温', '℃')
print("  (注意：1.7 小时数据里「漂移」多为环境慢变，非传感器真漂移，需更长数据确认)")

# ============ 5. 画图（快变 + 阈值线 + 异常点）============
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
idx = np.arange(len(ts))

for ax, fast, th, events, name, color in [
    (axes[0], hum_fast, hum_th, hum_events, 'HUMIDITY', '#22d3ee'),
    (axes[1], wt_fast,  wt_th,  wt_events,  'WATER TEMP', '#4ade80'),
]:
    ax.plot(idx, fast, color=color, lw=0.8)
    ax.axhline(0, color='#5b7a94', ls='--', lw=1)
    ax.axhline(th, color='#fbbf24', ls='--', lw=1.2, label=f'±{SIGMA:.0f}σ threshold')
    ax.axhline(-th, color='#fbbf24', ls='--', lw=1.2)
    # 标出异常段
    for e in events:
        start, end = e['start_idx'], e['end_idx']
        ax.plot(idx[start:end+1], fast[start:end+1], color='#f87171', lw=2)
    ax.set_title(f'{name}: fast component with anomaly marks (red)')
    ax.set_ylabel('fast'); ax.legend(loc='upper right'); ax.grid(alpha=0.3)

axes[1].set_xlabel('sample index')
fig.suptitle(f'Anomaly detection ({SIGMA:.0f}σ threshold, red = detected anomaly)', fontsize=13)
fig.tight_layout()
fig.savefig('anomaly_events.png', dpi=110)
print("\n已保存 anomaly_events.png")

# ============ 6. 保存异常事件清单 ============
result = {
    'sigma': SIGMA,
    'hum_threshold': round(hum_th, 4),
    'wt_threshold': round(wt_th, 4),
    'hum_events': hum_events,
    'wt_events': wt_events,
    'drift': {
        'hum_max_abs': round(hum_drift_max, 4),
        'hum_net': round(hum_drift_net, 4),
        'wt_max_abs': round(wt_drift_max, 4),
        'wt_net': round(wt_drift_net, 4),
    },
}
with open('anomaly_events.json', 'w') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
print("已保存 anomaly_events.json")
print("\n第 5 步完成。对照异常事件时间戳，看你「探头拿出水」那段对不对得上。")
