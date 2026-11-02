# -*- coding: utf-8 -*-
import threading
import json
import sqlite3
from collections import deque
import paho.mqtt.client as mqtt
from flask import Flask, jsonify, render_template, request

DB_PATH = '/userdata/project/lora_test/sensor.db'

app = Flask(__name__)

KEYS = ['temp', 'hum', 'press', 'tds', 'wt']
latest = {}
series = {}
alarms = {}


def on_message(client, userdata, msg):
    try:
        d = json.loads(msg.payload)
        bid = d.get('buoy', '#00')
        if msg.topic.endswith('/alarm'):
            al = alarms.setdefault(bid, deque(maxlen=50))
            al.append(d)
        else:
            latest[bid] = d
            s = series.setdefault(bid, {})
            for k in KEYS:
                s.setdefault(k, deque(maxlen=200)).append([d['ts'], d[k]])
    except Exception:
        pass


def mqtt_loop():
    c = mqtt.Client()
    c.on_message = on_message
    def on_connect(client, userdata, flags, rc):
        client.subscribe('buoy/#')
    c.on_connect = on_connect
    c.connect('localhost', 1883, 60)
    c.loop_forever()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/terminal')
def terminal():
    return render_template('index_terminal.html')


@app.route('/api/latest')
def api_latest():
    return jsonify(latest)


@app.route('/api/alarms')
def api_alarms():
    return jsonify({k: list(v) for k, v in alarms.items()})


@app.route('/api/series/<bid>')
def api_series(bid):
    bid = '#' + bid.lstrip('#')
    return jsonify({k: list(v) for k, v in series.get(bid, {}).items()})


@app.route('/api/history/<bid>')
def api_history(bid):
    bid = '#' + bid.lstrip('#')
    date = request.args.get('date', '')
    limit = int(request.args.get('limit', 500))
    try:
        db = sqlite3.connect(DB_PATH, timeout=5)
        if date:
            rows = db.execute(
                "SELECT ts,temp,hum,press,lat,lon,tds,wt FROM sensor_data "
                "WHERE buoy_id=? AND substr(ts,1,10)=? ORDER BY id DESC LIMIT ?",
                (bid, date, limit)).fetchall()
        else:
            rows = db.execute(
                "SELECT ts,temp,hum,press,lat,lon,tds,wt FROM sensor_data "
                "WHERE buoy_id=? ORDER BY id DESC LIMIT ?",
                (bid, limit)).fetchall()
        db.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/archive/dates')
def api_archive_dates():
    try:
        db = sqlite3.connect(DB_PATH, timeout=5)
        rows = db.execute(
            "SELECT DISTINCT substr(ts,1,10) AS d FROM sensor_data ORDER BY d DESC").fetchall()
        db.close()
        return jsonify([r[0] for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/archive/summary')
def api_archive_summary():
    bid = '#' + request.args.get('buoy', '#01').lstrip('#')
    try:
        db = sqlite3.connect(DB_PATH, timeout=5)
        db.execute('''CREATE TABLE IF NOT EXISTS daily_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buoy_id TEXT, day TEXT, count INTEGER,
            temp_avg REAL, temp_min REAL, temp_max REAL,
            hum_avg REAL, hum_min REAL, hum_max REAL,
            press_avg REAL, press_min REAL, press_max REAL,
            tds_avg REAL, tds_min REAL, tds_max REAL,
            wt_avg REAL, wt_min REAL, wt_max REAL,
            UNIQUE(buoy_id, day))''')
        recent = db.execute(
            "SELECT substr(ts,1,10) AS day, COUNT(*), "
            "ROUND(AVG(temp),2), ROUND(MIN(temp),2), ROUND(MAX(temp),2), "
            "ROUND(AVG(hum),2), ROUND(MIN(hum),2), ROUND(MAX(hum),2), "
            "ROUND(AVG(press),2), ROUND(MIN(press),2), ROUND(MAX(press),2), "
            "ROUND(AVG(tds),2), ROUND(MIN(tds),2), ROUND(MAX(tds),2), "
            "ROUND(AVG(wt),2), ROUND(MIN(wt),2), ROUND(MAX(wt),2) "
            "FROM sensor_data WHERE buoy_id=? GROUP BY day",
            (bid,)).fetchall()
        old = db.execute(
            "SELECT day, count, temp_avg, temp_min, temp_max, "
            "hum_avg, hum_min, hum_max, press_avg, press_min, press_max, "
            "tds_avg, tds_min, tds_max, wt_avg, wt_min, wt_max "
            "FROM daily_summary WHERE buoy_id=?", (bid,)).fetchall()
        db.close()
        merged = list(old) + list(recent)
        merged.sort(key=lambda x: x[0], reverse=True)
        return jsonify(merged)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.after_request
def add_no_cache(resp):
    resp.headers['Cache-Control'] = 'no-store'
    return resp


if __name__ == '__main__':
    threading.Thread(target=mqtt_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
