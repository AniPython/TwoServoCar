
"""
joystick mode 数据样例
b'\xff\x01\x02\x01\x02\x00\xb6\x00'
b'\xff\x01\x02\x01\x02\x00\xaf\x00'
b'\xff\x01\x02\x01\x02\x00>\x00',
b'\xff\x01\x02\x01\x02\x00?\x00',
"""
import math

class DabbleJoystick:
    # Connection status
    CONNECTED = b'\xff\x00\x03\x00\x00\x00'

    # button press
    # Left joystick
    LEFT_UP_PRESS = b'\xff\x01\x01\x01\x02\x00\x01\x00'
    LEFT_DOWN_PRESS = b'\xff\x01\x01\x01\x02\x00\x02\x00'
    LEFT_LEFT_PRESS = b'\xff\x01\x01\x01\x02\x00\x04\x00'
    LEFT_RIGHT_PRESS = b'\xff\x01\x01\x01\x02\x00\x08\x00'

    # Right joystick
    RIGHT_UP_PRESS = b'\xff\x01\x01\x01\x02\x04\x00\x00'
    RIGHT_DOWN_PRESS = b'\xff\x01\x01\x01\x02\x10\x00\x00'
    RIGHT_LEFT_PRESS = b'\xff\x01\x01\x01\x02\x20\x00\x00'
    RIGHT_RIGHT_PRESS = b'\xff\x01\x01\x01\x02\x08\x00\x00'

    # Start and Select
    START_PRESS = b'\xff\x01\x01\x01\x02\x01\x00\x00'
    SELECT_PRESS = b'\xff\x01\x01\x01\x02\x02\x00\x00'

    # button release
    RELEASE = b'\xff\x01\x01\x01\x02\x00\x00\x00'

    @staticmethod
    def parse_joystick_data_to_coordinate(data):
        """
        返回 x, y 坐标的 float 类型元组
        x, y 坐标为: -7 ~ 7
        """
        try:
            value = data[6]
            angle = ((value >> 3) * 15)
            radius = value & 0x07
            return radius * math.cos(math.radians(angle)), radius * math.sin(math.radians(angle))

        except Exception as e:
            print("Invalid joystick data:", e)

# Example usage
if __name__ == "__main__":
    # Accessing an Enum value
    print(DabbleJoystick.LEFT_UP_PRESS)  # Outputs: b'\xff\x01\x01\x01\x02\x00\x01\x00'

