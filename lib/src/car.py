import time
from machine import PWM, Pin


class Car:

    def __init__(self, left_pin, pin_right, zero_duty=76, duty_limit=35,
                 hand_pin=None, hand_init_angle=90, step=3):
        self.left_pwm = PWM(Pin(left_pin), freq=50)
        self.right_pwm = PWM(Pin(pin_right), freq=50)
        self.zero_duty = zero_duty
        self.duty_limit = duty_limit
        self.hand_pin = hand_pin
        self.hand_init_angle = hand_init_angle
        self.current_hand_angle = hand_init_angle
        self.step = step
        if self.hand_pin:
            self.hand_pwm = PWM(Pin(self.hand_pin), freq=50)
            self.set_hand_servo_angle(self.current_hand_angle)

    def stop(self):
        self.left_pwm.duty(0)
        self.right_pwm.duty(0)
        time.sleep(0.6)
        print("Motor stopped!")

    def set_speed(self, left_speed, right_speed):
        left_speed = int(left_speed)
        right_speed = int(right_speed)

        # left_speed = self.limit_value(left_speed, -self.duty_limit, self.duty_limit)
        # right_speed = self.limit_value(right_speed, -self.duty_limit, self.duty_limit)

        self.left_pwm.duty(self.zero_duty + left_speed)
        self.right_pwm.duty(self.zero_duty - right_speed)

    def joystick_coordinate_to_motor_speed(self, x, y):
        # -7 ~ 7 归一化到 -1 ~ 1
        x_norm = x / 7
        y_norm = y / 7

        # 计算左右轮速度
        v_left = y_norm * self.duty_limit + x_norm * self.duty_limit
        v_right = y_norm * self.duty_limit - x_norm * self.duty_limit

        # 限制范围到 -35 ~ 35
        v_left = max(min(v_left, self.duty_limit), -self.duty_limit)
        v_right = max(min(v_right, self.duty_limit), -self.duty_limit)

        return int(v_left), int(v_right)

    @staticmethod
    def limit_value(value, min_value, max_value):
        return max(min_value, min(max_value, value))

    def hand_up(self):
        self.current_hand_angle = self.current_hand_angle - self.step
        self.set_hand_servo_angle(self.current_hand_angle)

    def hand_down(self):
        self.current_hand_angle = self.current_hand_angle + self.step
        self.set_hand_servo_angle(self.current_hand_angle)

    def set_hand_servo_angle(self, angle):
        duty = int(angle * 102 / 180 + 26)
        self.hand_pwm.duty(duty)
