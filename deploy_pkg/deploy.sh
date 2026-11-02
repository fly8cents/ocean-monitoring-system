#!/bin/bash
set -e
APP_DIR="/userdata/project/lora_test"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "======== 1/7 检查/安装 mosquitto ========"
if ! command -v mosquitto &>/dev/null; then
    echo "mosquitto 未安装，正在安装..."
    apt-get update && apt-get install -y mosquitto mosquitto-clients
fi
systemctl enable --now mosquitto 2>/dev/null || mosquitto -d

echo "======== 2/7 安装 Python 依赖 ========"
pip3 install pyserial paho-mqtt flask

echo "======== 3/7 部署文件 ========"
mkdir -p "$APP_DIR/templates" "$APP_DIR/static"
cp "$SCRIPT_DIR/data_process.py" "$SCRIPT_DIR/app.py" "$SCRIPT_DIR/archive.py" "$SCRIPT_DIR/anomaly_detector.py" "$APP_DIR/"
cp "$SCRIPT_DIR/templates/"*.html "$APP_DIR/templates/" 2>/dev/null || true
cp "$SCRIPT_DIR/static/"*.json "$APP_DIR/static/" 2>/dev/null || true

echo "======== 4/7 创建 systemd 服务 ========"
cat > /etc/systemd/system/ocean-data.service << EOF
[Unit]
Description=Ocean Sensor Data Process
After=network.target mosquitto.service

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 -u $APP_DIR/data_process.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/ocean-web.service << EOF
[Unit]
Description=Ocean Monitor Web UI
After=network.target mosquitto.service ocean-data.service

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 -u $APP_DIR/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "======== 5/7 配置归档定时 ========"
(crontab -l 2>/dev/null | grep -v archive.py; echo "0 3 * * * /usr/bin/python3 $APP_DIR/archive.py >> $APP_DIR/archive.log 2>&1") | crontab -

echo "======== 6/7 配置上云桥接 ========"
if [ -f "$SCRIPT_DIR/mosquitto-bridge.conf" ]; then
    BRIDGE_ID="ocean-bridge-$(hostname | tr -cd 'a-zA-Z0-9' | head -c 8)"
    [ -z "$BRIDGE_ID" ] && BRIDGE_ID="ocean-bridge-default"
    sed "s/__CLIENTID__/$BRIDGE_ID/" "$SCRIPT_DIR/mosquitto-bridge.conf" \
        > /etc/mosquitto/conf.d/bridge-cloud.conf
    systemctl restart mosquitto 2>/dev/null || mosquitto -d
    echo "✅ 上云桥接已配置（clientid=$BRIDGE_ID，buoy/# → 云端 broker）"
else
    echo "⚠️  未找到 mosquitto-bridge.conf，跳过上云（仅本地模式）"
fi

echo "======== 7/7 启动服务 + 检查 ========"
systemctl daemon-reload
systemctl enable ocean-data ocean-web
systemctl restart ocean-data ocean-web

IP=$(hostname -I | awk '{print $1}')
echo ""
echo "======== 部署完成 ========"
echo "数据采集日志: journalctl -u ocean-data -f"
echo "Web 大屏访问: http://$IP:5000/terminal"
echo ""
echo "服务状态:"
systemctl is-active mosquitto ocean-data ocean-web
echo ""
if [ -e /dev/ttyUSB0 ]; then
    echo "✅ 检测到 LoRa 串口 /dev/ttyUSB0"
else
    echo "⚠️  未检测到 /dev/ttyUSB0，请检查 LoRa USB 是否插入"
fi
