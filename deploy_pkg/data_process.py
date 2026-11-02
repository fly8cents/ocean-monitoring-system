import serial
from collections import deque, defaultdict
import time
import sqlite3
import json
import paho.mqtt.client as mqtt
from anomaly_detector import AnomalyDetector

ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)

WINDOW = 10

history = defaultdict(lambda: {
    'temp': deque(maxlen=WINDOW), 'hum': deque(maxlen=WINDOW),
    'press': deque(maxlen=WINDOW), 'tds': deque(maxlen=WINDOW),
    'wt': deque(maxlen=WINDOW),
})
last_avg = {}

THRESHOLD = {
    'temp': (-40, 85), 'hum': (0, 100), 'press': (800, 1100),
    'tds': (0, 2000), 'wt': (-10, 60),
}
DELTA = {
    'temp': 5.0, 'hum': 20.0, 'press': 10.0, 'tds': 100.0, 'wt': 5.0,
}

db = sqlite3.connect('/userdata/project/lora_test/sensor.db')
db.execute('''CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buoy_id TEXT, ts TEXT, temp REAL, hum REAL, press REAL,
    lat REAL, lon REAL, tds REAL, wt REAL)''')

mqttc = mqtt.Client()
mqttc.connect("localhost", 1883, 60)
mqttc.loop_start()

A1, B1 = -2.2200, 114.0921
A2, B2 = 0.6908, 7.3178
detectors = {}

def parse(line):
    if not line.startswith('#'):
        return None
    p = line.split(',')
    return {'id': p[0], 'temp': float(p[1]), 'hum': float(p[2]),
            'press': float(p[3]), 'lat': float(p[4]), 'lon': float(p[5]),
            'tds': float(p[6]), 'wt': float(p[7])}

print("开始接收多浮标数据...")
while True:
    line = ser.readline().decode('utf-8', errors='ignore').strip()
    data = parse(line)
    if data is None:
        continue

    bid = data['id']
    h = history[bid]
    for k in ['temp', 'hum', 'press', 'tds', 'wt']:
        h[k].append(data[k])

    if len(h['temp']) >= 5:
        avg = {k: round(sum(h[k])/len(h[k]), 2) for k in h}

        alarms = []
        for k in ['temp', 'hum', 'press', 'tds', 'wt']:
            lo, hi = THRESHOLD[k]
            if avg[k] < lo or avg[k] > hi:
                alarms.append(k + "超范围")
            if bid in last_avg and abs(avg[k] - last_avg[bid][k]) > DELTA[k]:
                alarms.append(k + "突变")
        last_avg[bid] = avg
        status = " ⚠" + ",".join(alarms) if alarms else " 正常"

        db.execute("INSERT INTO sensor_data (buoy_id,ts,temp,hum,press,lat,lon,tds,wt) "
                   "VALUES (?,?,?,?,?,?,?,?,?)",
                   (bid, time.strftime('%Y-%m-%d %H:%M:%S'),
                    avg['temp'], avg['hum'], avg['press'],
                    data['lat'], data['lon'], avg['tds'], avg['wt']))
        db.commit()

        payload = json.dumps({
            "buoy": bid, "ts": time.strftime('%Y-%m-%d %H:%M:%S'),
            "temp": avg['temp'], "hum": avg['hum'], "press": avg['press'],
            "lat": data['lat'], "lon": data['lon'],
            "tds": avg['tds'], "wt": avg['wt'],
        })
        mqttc.publish(f"buoy/{bid[1:]}/data", payload)

        if bid not in detectors:
            detectors[bid] = AnomalyDetector(A1, B1, A2, B2, window=20, sigma=3.0)
        r = detectors[bid].update(avg['temp'], avg['hum'], avg['wt'])
        if r.get('ready') and (r['hum_alarm'] or r['wt_alarm']):
            alarm = {
                "buoy": bid, "ts": time.strftime('%Y-%m-%d %H:%M:%S'),
                "type": "physical_inconsistency",
                "hum_alarm": r['hum_alarm'], "wt_alarm": r['wt_alarm'],
                "hum_fast": r['hum_fast'], "wt_fast": r['wt_fast'],
            }
            mqttc.publish(f"buoy/{bid[1:]}/alarm", json.dumps(alarm))
            print(f"  ⚠ 物理一致性异常 {bid}: 湿度快变={r['hum_fast']} 水温快变={r['wt_fast']}")

        print(f"{bid} 气温:{avg['temp']} 湿度:{avg['hum']} "
              f"气压:{avg['press']} TDS:{avg['tds']} 水温:{avg['wt']}{status}")

    time.sleep(0.01)
