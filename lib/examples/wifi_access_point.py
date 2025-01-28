"""
Wifi Access Point(AP_IF) 模式 esp32 充当 无线接入点, 不需要连路由器, 手机直接使用 wifi 连 esp32
"""

from time import sleep
from machine import Pin
import network
import ubinascii

ap_if = None

SSID = 'Name of Network'
PASSWORD = 'Password of Network'
# x y 需要替换
# x: 是 esp32 中设置的局网段
# y: 是本机IP, 范围在 1~254
IFCONFIG = ("192.168.x.y", "255.255.255.0", "192.168.x.1", "8.8.8.8")

led = Pin(2, Pin.OUT)
led.off()
def create_ap():
    global ap_if
    ap_if = network.WLAN(network.AP_IF)
    ap_if.ifconfig(IFCONFIG)
    ap_if.active(True)
    ap_if.config(essid=SSID, password=PASSWORD, authmode=network.AUTH_WPA2_PSK)
    print("Action Point is created.The MAC address is: ", ubinascii.hexlify(ap_if.config('mac'), ':').decode().upper())
    print("The network values are: ", ap_if.ifconfig())

create_ap()

while True:
    if ap_if.isconnected():
        led.on()
        sleep(0.5)
        led.off()
        sleep(0.5)
    else:
        led.off()

