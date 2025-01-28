"""
Wifi Station(STA_IF) 模式 esp32 充当客户端设备, 需要连路由器
"""

from time import sleep                     #importing sleep class
from machine import Pin
import network
import ubinascii

sta_if = None
SSID = 'Name of Network'
PASSWORD = 'Password of Network'
# x y 需要替换
# x: 是路由器中设置的局网段
# y: 是本机IP, 范围在 1~254
IFCONFIG = ("192.168.x.y", "255.255.255.0", "192.168.x.1", "8.8.8.8")

led = Pin(2, Pin.OUT) # Built in LED
led.off()
def do_sta_connect():
    global sta_if
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        sta_if.ifconfig(IFCONFIG)
        sta_if.active(True)
        sta_if.connect(SSID, PASSWORD)
    print("Connecting to network ...")
    while not sta_if.isconnected():
        pass
    print("Connected.The MAC address is: ", ubinascii.hexlify(sta_if.config('mac'), ':').decode().upper())
    print("The network values are: ", sta_if.ifconfig())

do_sta_connect()

while True:
    led.on()
    sleep(0.5)
    led.off()
    sleep(0.5)
