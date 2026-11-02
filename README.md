# Ocean Monitoring System

Near-shore buoy monitoring: STM32 sensor node + RK3566 edge gateway with physical-consistency anomaly detection.

## Directory Structure

```
├── stm32/              # STM32 buoy sensor node (CubeIDE project)
│   └── SensorHub/
├── deploy_pkg/         # RK3566 gateway deployment package
├── edge_ai/            # offline analysis scripts for anomaly detection
└── index_cloud.html    # cloud realtime dashboard (static)
```

---

## STM32 — Buoy Sensor Node

### Requirements

- STM32CubeIDE 1.16
- ST-Link programmer

### Open the project

1. STM32CubeIDE → **File → Open Projects from File System** → **Directory...** → select `stm32/SensorHub`
2. Click **Finish**

### Build

**Project → Build All** (or `Ctrl+B`)

### Flash (ST-Link)

1. Wire: `SWDIO → PA13`, `SWCLK → PA14`, `GND → GND`, `3.3V → 3.3V`
2. Set BOOT0 jumper to **0** (GND side)
3. **Run → Run** (or the green Run button)

> If the chip is locked ("Target is not responding"), hold RESET → click Download → release RESET right after it connects.

### Sensor wiring

| Sensor | Interface | MCU pins |
|---|---|---|
| AHT20 (temp / humidity) | I2C1, addr `0x38` | SCL=`PB6`, SDA=`PB7` |
| BMP280 (pressure) | I2C1, addr `0x77` | SCL=`PB6`, SDA=`PB7` |
| GPS ATGM336H | USART2, 9600 | TX=`PA2`, RX=`PA3` |
| TDS probe | USART3, 9600 | TX=`PB10`, RX=`PB11` |
| LoRa E22 (transmit) | USART1, 9600 | TX=`PA9`, RX=`PA10`, **M0=M1=GND** |

> AHT20 and BMP280 share the same I2C bus (SCL/SDA wired in parallel), distinguished by address.

---

## RK3566 Gateway — deploy_pkg

### Package contents

| File | Purpose |
|---|---|
| `deploy.sh` | one-click deploy script |
| `data_process.py` | LoRa receive → filter → SQLite → MQTT → anomaly detection |
| `anomaly_detector.py` | A+B physical-consistency anomaly detection module |
| `app.py` | Flask web backend |
| `archive.py` | daily data archiving (cron) |
| `mosquitto-bridge.conf` | MQTT cloud uplink bridge config |
| `templates/` | web dashboard (terminal-style) |
| `static/` | map geoJSON |

### Requirements

- RK3566 board running Debian/Ubuntu
- Internet access for `apt` / `pip`

### Deploy

```bash
scp -r deploy_pkg root@<RK3566_IP>:/tmp/
ssh root@<RK3566_IP> "cd /tmp/deploy_pkg && bash deploy.sh"
```

The script automatically: installs mosquitto, installs Python deps, deploys files, creates systemd services, configures cron archiving, configures 4G cloud bridge (if `mosquitto-bridge.conf` present), and restarts services.

### Verify

```bash
# data collection log
journalctl -u ocean-data -f

# web dashboard
# http://<RK3566_IP>:5000/terminal
```

### Cloud uplink

- Local mosquitto bridges `buoy/#` to `broker.emqx.io` (public broker, for demo only);
- Remove `mosquitto-bridge.conf` to disable uplink (local-only mode);
- For production, change `address` in `mosquitto-bridge.conf` to your own broker.
