"""
接收 json 格式数据
{
    "left_speed": int,
    "right_speed": int,
}
来控制小车运动
"""

import network
import socket
import ujson
from time import sleep
from car import Car


# Wifi
ssid = "小亦站"
password = "88889999"
ifconfig = ("192.168.2.180", "255.255.255.0", "192.168.2.1", "8.8.8.8")

wlan = network.WLAN(network.STA_IF)
wlan.ifconfig(ifconfig)
wlan.active(True)
wlan.connect(ssid, password)
print('Connecting to WiFi...', end='')
while not wlan.isconnected():
    sleep(0.5)
    print('.', end='')
print('\nConnection successful')
print(wlan.ifconfig())

# Car
car = Car(left_pin=14, pin_right=13)
car.set_speed(0, 0)

# Socket
port = 12345
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(1)
sock.bind(('', port))
print(f'Socket receive control data listening on port {port}')

while True:
    try:
        data, addr = sock.recvfrom(1024)
        params = ujson.loads(data.decode())
        print(params)
        assert isinstance(params, dict), 'params must be dict'
        assert 'left_speed' in params, 'params must have left_speed'
        assert 'right_speed' in params, 'params must have right_speed'

        car.set_speed(int(params['left_speed']), int(params['right_speed']))

    except OSError as e:
        print(e)
        car.set_speed(0, 0)

