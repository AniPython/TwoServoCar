import cv2
import numpy as np
import json
import socket
import math

import time


# 初始化摄像头
cap = cv2.VideoCapture(0)

# 设置 ArUco 字典和参数
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_250)
parameters = cv2.aruco.DetectorParameters()
detector= cv2.aruco.ArucoDetector(aruco_dict, parameters)

# 创建 UDP 客户端
esp32_ip = "192.168.2.180"  # ESP32 的 IP 地址
esp32_port = 12345  # ESP32 接收端口
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

CAR_ARUCO_ID = 3
CTRL_ARUCO_ID = 0


k_rad = 12
k_speed = 0.08

# 计算左右轮速度
def calculate_wheel_speeds(radian, speed):
    max_speed = 35  # 最大速度
    left_speed = max(min(speed - radian, max_speed), -max_speed)
    right_speed = max(min(speed + radian, max_speed), -max_speed)
    return left_speed, right_speed


def calculate_corner_radian(corner):
    corner = corner.squeeze()
    corner_radian = math.atan2(corner[1, 1] - corner[0, 1], corner[1, 0] - corner[0, 0])
    return corner_radian

def calculate_2corner_radian_diff(corner1, corner2):
    corner1 = corner1.squeeze()
    corner2 = corner2.squeeze()

    vector1 = corner1[0] - corner1[1]
    vector2 = corner2[0] - corner2[1]
    corner_radian_diff =  np.arctan2(vector1[1], vector1[0]) - np.arctan2(vector2[1], vector2[0])
    return corner_radian_diff

while True:
    ret, frame = cap.read()
    if not ret:
        break

    WIDTH, HEIGHT = frame.shape[1], frame.shape[0]

    # 检测 ArUco 标记
    # corners, ids, _ = cv2.aruco.detectMarkers(frame, aruco_dict, parameters=parameters)
    # corners, ids = aruco_detect(aruco_detector, image, is_show=True)

    corners, ids, _ = detector.detectMarkers(frame)

    control_data = {
        "left_speed": 0,
        "right_speed": 0
    }

    if ids is not None and len(ids) == 2 and  CAR_ARUCO_ID in ids and CTRL_ARUCO_ID in ids:
        for i, corner in zip(ids.flatten(), corners):
            # 识别小车 ArUco（编号为0）和遥控器 ArUco（其他编号）
            if i == CAR_ARUCO_ID:  # 小车的 ArUco（编号为0）
                car_corners = corner
                car_center = np.mean(car_corners, axis=1).flatten()
                car_radian = calculate_corner_radian(car_corners)
                # print(f"car_radian: {car_radian}")
                cv2.circle(frame, tuple(car_center.astype(int)), 5, (0, 0, 255), -1)
            if i == CTRL_ARUCO_ID:  # 遥控器的 ArUco
                remote_corners = corner
                remote_center = np.mean(remote_corners, axis=1).flatten()
                remote_radian = calculate_corner_radian(remote_corners)
                # print(f"remote_radian: {remote_radian}")
                cv2.circle(frame, tuple(remote_center.astype(int)), 5, (0, 255, 0), -1)

        # 计算遥控器的角度（屏幕水平与垂直方向）
        # radian_diff = car_radian - remote_radian
        speed = remote_center[1] - HEIGHT / 2  # 用遥控器垂直方向的位置来控制速度

        radian_diff = calculate_2corner_radian_diff(car_corners, remote_corners)
        if radian_diff > math.pi:
            radian_diff -= 2 * math.pi
        elif radian_diff < -math.pi:
            radian_diff += 2 * math.pi
        # print(f"radian_diff: {radian_diff}")

        # print(f"Angle: {angle}, Speed: {speed}")
        # time.sleep(0.8)

        # 计算左右轮速度
        left_speed, right_speed = calculate_wheel_speeds(radian_diff * k_rad, speed * k_speed)

        # 发送数据到 ESP32
        control_data = {
            "left_speed": int(left_speed),
            "right_speed": int(right_speed)
        }

    try:
        sock.sendto(json.dumps(control_data).encode(), (esp32_ip, esp32_port))
    except OSError as e:
        pass
        # print(f"Error sending data to ESP32: {e}")

    # print(control_data)
    # time.sleep(0.2)

    # 显示处理后的图像
    cv2.imshow('Frame', frame)

    # 按键 'q' 退出
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
sock.close()
