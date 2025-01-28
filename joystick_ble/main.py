import time
from car import Car
from esp32ble import ESP32_BLE
from dabble_joystick import DabbleJoystick

# 初始化 BLE
ble = ESP32_BLE(name="MPY ESP32")
car = Car(left_pin=14, pin_right=13, hand_pin=26, hand_init_angle=90)


# 当收到 BLE 数据时执行
def on_rx(data):
    if len(data) == 8:
        if data[2] == 0x01:  # 按钮
            if data == DabbleJoystick.RIGHT_UP_PRESS:
                car.hand_up()
            elif data == DabbleJoystick.RIGHT_DOWN_PRESS:
                car.hand_down()
        elif data[2] == 0x02:  # 摇杆
            x, y = DabbleJoystick.parse_joystick_data_to_coordinate(data)
            left_speed, right_speed = car.joystick_coordinate_to_motor_speed(x, y)
            car.set_speed(left_speed, right_speed)


ble.on_write(on_rx)

# 主循环
while True:
    time.sleep(0.1)
    pass
