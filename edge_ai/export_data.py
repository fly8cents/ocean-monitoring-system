#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出训练数据：从 sensor.db 导出传感器数据到 CSV，用于训练自编码器。
在 RK3566 上运行：python3 export_data.py
"""
import sqlite3
import csv

DB = '/userdata/project/lora_test/sensor.db'
OUT = 'train_data.csv'

db = sqlite3.connect(DB)
rows = db.execute(
    "SELECT ts, temp, hum, press, tds, wt FROM sensor_data "
    "WHERE temp IS NOT NULL AND hum IS NOT NULL AND press IS NOT NULL "
    "AND tds IS NOT NULL AND wt IS NOT NULL ORDER BY id").fetchall()
db.close()

with open(OUT, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['ts', 'temp', 'hum', 'press', 'tds', 'wt'])
    w.writerows(rows)

print(f"导出 {len(rows)} 条数据到 {OUT}")
