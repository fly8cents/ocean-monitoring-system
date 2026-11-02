#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
import time

DB = '/userdata/project/lora_test/sensor.db'
KEEP_DETAIL_DAYS = 7
KEEP_SUMMARY_DAYS = 365

CREATE = '''CREATE TABLE IF NOT EXISTS daily_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buoy_id TEXT, day TEXT,
    count INTEGER,
    temp_avg REAL, temp_min REAL, temp_max REAL,
    hum_avg REAL, hum_min REAL, hum_max REAL,
    press_avg REAL, press_min REAL, press_max REAL,
    tds_avg REAL, tds_min REAL, tds_max REAL,
    wt_avg REAL, wt_min REAL, wt_max REAL,
    UNIQUE(buoy_id, day))'''


def archive():
    cutoff = time.strftime('%Y-%m-%d', time.localtime(time.time() - KEEP_DETAIL_DAYS * 86400))
    summary_cutoff = time.strftime('%Y-%m-%d', time.localtime(time.time() - KEEP_SUMMARY_DAYS * 86400))

    db = sqlite3.connect(DB, timeout=10)
    db.execute("PRAGMA busy_timeout=10000")
    db.execute(CREATE)

    rows = db.execute(
        "SELECT buoy_id, substr(ts,1,10) AS day, COUNT(*), "
        "AVG(temp), MIN(temp), MAX(temp), AVG(hum), MIN(hum), MAX(hum), "
        "AVG(press), MIN(press), MAX(press), AVG(tds), MIN(tds), MAX(tds), "
        "AVG(wt), MIN(wt), MAX(wt) "
        "FROM sensor_data WHERE substr(ts,1,10) < ? "
        "GROUP BY buoy_id, day", (cutoff,)).fetchall()

    for r in rows:
        db.execute(
            "INSERT OR REPLACE INTO daily_summary "
            "(buoy_id, day, count, "
            "temp_avg, temp_min, temp_max, hum_avg, hum_min, hum_max, "
            "press_avg, press_min, press_max, tds_avg, tds_min, tds_max, "
            "wt_avg, wt_min, wt_max) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", r)

    n_del = db.execute("DELETE FROM sensor_data WHERE substr(ts,1,10) < ?", (cutoff,)).rowcount
    db.execute("DELETE FROM daily_summary WHERE day < ?", (summary_cutoff,))

    db.commit()
    db.close()
    print(f"[archive] 归档 {len(rows)} 天次汇总，删除 {n_del} 条旧明细 "
          f"(明细保留到 {cutoff}，汇总保留到 {summary_cutoff})")


if __name__ == '__main__':
    archive()
