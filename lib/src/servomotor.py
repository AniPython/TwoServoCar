import time
from machine import PWM, Pin


class ServoMotorController:

    def __init__(self, left_pin, pin_right, zero_duty=76, duty_limit=35):
        self.left_pwm = PWM(Pin(left_pin))
        self.left_pwm.freq(50)
        self.right_pwm = PWM(Pin(pin_right))
        self.right_pwm.freq(50)
        self.zero_duty = zero_duty
        self.duty_limit = duty_limit

    def stop(self):
        self.left_pwm.duty(0)
        self.right_pwm.duty(0)
        time.sleep(0.6)
        print("Motor stopped!")

    def set_speed(self, left_speed, right_speed):
        left_speed = int(left_speed)
        right_speed = int(right_speed)

        left_speed = self.limit_value(left_speed, -self.duty_limit, self.duty_limit)
        right_speed = self.limit_value(right_speed, -self.duty_limit, self.duty_limit)

        self.left_pwm.duty(self.zero_duty + left_speed)
        self.right_pwm.duty(self.zero_duty - right_speed)

    @staticmethod
    def limit_value(value, min_value, max_value):
        return max(min_value, min(max_value, value))
