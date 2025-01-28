import socket
from errno import ETIMEDOUT

from machine import PWM, Pin
import network
import time
import ujson
import _thread
from collections import OrderedDict


a_lock = _thread.allocate_lock()



run_data = {
    'angle': 0,
    'distance': 0,
    'status': 0,  # 0: 没有发现目标, 1: 追踪小球, 2: 追踪小球成功, 3: 追踪小球目的地(运送小球), 4: 小球成功到达目的地
}

last_run_data = {
    'angle': 0,
    'distance': 0,
    'status': 0,  # 0: 没有发现目标, 1: 追踪小球, 2: 追踪小球成功, 3: 追踪小球目的地(运送小球), 4: 小球成功到达目的地
}

hand_up_angle = 45
hand_down_angle = 110

def limit_value(value, min_value=0, max_value=1023):
    return max(min_value, min(max_value, value))

class WiFiManager:
    def __init__(self, ssid, password, ifconfig):
        self.ssid = ssid
        self.password = password
        self.ifconfig = ifconfig

    def connect(self):
        wlan = network.WLAN(network.STA_IF)
        wlan.ifconfig(self.ifconfig)
        wlan.active(True)
        wlan.connect(self.ssid, self.password)
        print('Connecting to WiFi...', end='')
        while not wlan.isconnected():
            time.sleep(0.5)
            print('.', end='')
        print('\nConnection successful')
        print(wlan.ifconfig())


class MotorController:
    zero_duty = 76
    duty_limit = 35

    def __init__(self, left_pin, pin_right):
        self.left_pwm = PWM(Pin(left_pin))
        self.left_pwm.freq(50)
        self.right_pwm = PWM(Pin(pin_right))
        self.right_pwm.freq(50)

    def stop(self):
        self.left_pwm.duty(0)
        self.right_pwm.duty(0)
        time.sleep(0.6)
        print("Motor stopped!")

    def set_speed(self, left_speed, right_speed):
        left_speed = int(left_speed)
        right_speed = int(right_speed)

        left_speed = limit_value(left_speed, -self.duty_limit, self.duty_limit)
        right_speed = limit_value(right_speed, -self.duty_limit, self.duty_limit)

        self.left_pwm.duty(self.zero_duty + left_speed)
        self.right_pwm.duty(self.zero_duty - right_speed)


class PIDController:
    def __init__(self, initial_data):

        self.pid_data = OrderedDict(initial_data)
        self.pid_data_default = self.pid_data.copy()

        self.pre_error_distance = 0
        self.pre_error_angle = 0
        self.integral_distance = 0
        self.integral_angle = 0

    def update_params(self, params):
        self.pid_data.update(params)
        print(f"Updated PID parameters: \n{self.pid_data}\n")

    def set_default(self):
        self.pid_data = self.pid_data_default.copy()
        print(f"Set PID parameters to default: \n{self.pid_data}\n")

    def zero(self):
        self.integral_distance = 0
        self.integral_angle = 0
        self.pre_error_distance = 0
        self.pre_error_angle = 0

    def calculate(self, angle, distance):
        # Calculate distance error
        error_distance = distance - self.pid_data["target_distance"]
        self.integral_distance += error_distance
        diff_distance = error_distance - self.pre_error_distance
        self.pre_error_distance = error_distance

        # Calculate angle error
        error_angle = angle - self.pid_data["target_angle"]
        self.integral_angle += error_angle
        diff_angle = error_angle - self.pre_error_angle
        self.pre_error_angle = error_angle

        # PID control calculations
        control_signal_distance = (
                self.pid_data["kp_distance"] * error_distance +
                self.pid_data["ki_distance"] * self.integral_distance +
                self.pid_data["kd_distance"] * diff_distance
        )
        control_signal_angle = (
                self.pid_data["kp_angle"] * error_angle +
                self.pid_data["ki_angle"] * self.integral_angle +
                self.pid_data["kd_angle"] * diff_angle
        )

        # Calculate left and right wheel speeds
        left_speed = int(control_signal_distance + control_signal_angle)
        right_speed = int(control_signal_distance - control_signal_angle)

        return left_speed, right_speed


class ControlHandler:
    def __init__(self,
                 motor_controller: MotorController,
                 pid_controller: PIDController):
        self.motor_controller = motor_controller
        self.pid_controller = pid_controller


    def run(self):
        global run_data, last_run_data
        PWM(Pin(2, Pin.OUT)).duty(512)
        while True:
            angle = run_data.get('angle')
            distance = run_data.get('distance')
            # status = run_data.get('status')
            if angle == 0 and distance == 0:
                self.motor_controller.stop()
                continue

            left_speed, right_speed = self.pid_controller.calculate(angle, distance)
            self.motor_controller.set_speed(left_speed, right_speed)



def start_udp_recv_data_thread(controller, port):
    global run_data
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    sock.bind(('', port))
    print(f'Socket receive control data listening on port {port}')
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            params = ujson.loads(data.decode())

            if 'angle' in params:
                run_data['angle'] = params.get('angle')
                run_data['distance'] = params.get('distance')
                run_data['status'] = params.get('status')

        except OSError as e:
            run_data['angle'] = 0
            run_data['distance'] = 0
            run_data['status'] = 0

def blink():
    led_pwm = PWM(Pin(2, Pin.OUT))
    while True:
        led_pwm.duty(512)
        time.sleep(0.5)
        led_pwm.duty(0)
        time.sleep(0.5)


if __name__ == '__main__':
    # 配置参数
    SSID = '小亦站'
    PASSWORD = '88889999'
    IFCONFIG = ("192.168.2.180", "255.255.255.0", "192.168.2.1", "8.8.8.8")
    PORT_DATA = 10000  # 收 控制指令
    PC_IP = "192.168.2.66"

    # PID 控制参数初始化
    pid_initial_data = [
        ("kp_distance", 0.05),
        ("ki_distance", 0),
        ("kd_distance", 0),
        ("kp_angle", 0.25),
        ("ki_angle", 0),
        ("kd_angle", 0),
        ("target_angle", 0),
        ("target_distance", 10)
    ]

    # 创建对象
    wifi_manager = WiFiManager(SSID, PASSWORD, IFCONFIG)
    motor_controller = MotorController(14, 13)
    pid_controller = PIDController(pid_initial_data)
    data_handler = ControlHandler(motor_controller, pid_controller)

    # 连接 WiFi
    wifi_manager.connect()

    # 启动线程
    # 1. 接收 angle 和 distance
    _thread.start_new_thread(start_udp_recv_data_thread, (pid_controller, PORT_DATA))

    # 主线程
    # blink()
    data_handler.run()

