import cv2
import numpy as np
import socket
import json

from consts import *

is_sendto_esp32 = True
sock_udp = None
image_show = None
car_center = (0, 0)

def get_corner_edge_length(corner: np.typing.ArrayLike) -> float:
    corner = corner.squeeze()
    return np.sqrt(np.square(corner[0][0] - corner[1][0]) + np.square(corner[0][1] - corner[1][1]))


def update_k(car_corner: np.typing.ArrayLike):
    global k
    # 获取 car_corner 的边长
    edge_length = get_corner_edge_length(car_corner)
    # print("edge_length_px: ", edge_length)
    k = edge_length / CAR_ARUCO_SIZE_MM

def default_4x4_aruco_detector():
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_250)
    detector_params = cv2.aruco.DetectorParameters()
    return cv2.aruco.ArucoDetector(dictionary, detector_params)


def aruco_detect(detector, image: np.typing.ArrayLike, is_show=False):
    # 将 BGR 图像转换为灰度图像
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # 如果噪声明显，用中值滤波去噪
    image = cv2.medianBlur(image, 5)
    # 使用高斯模糊进一步平滑图像
    image = cv2.GaussianBlur(image, (5, 5), 0)
    # 使用 Otsu 阈值法进行二值化（更适合光照不均匀的场景）
    ret, image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 使用检测器检测图像中的ARuco标记
    corners, ids, _ = detector.detectMarkers(image)
    if is_show:
        cv2.aruco.drawDetectedMarkers(image, corners, ids)
        cv2.imshow("blur out", image)
        key = cv2.waitKey(1)
        if key == 27:  # esc 键退出
            cv2.destroyAllWindows()
    return corners, ids


def main():
    global sock_udp, image_show, WIDTH, HEIGHT, status, car_center

    if is_sendto_esp32:
        sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 创建ArUco探测器对象
    aruco_detector = default_4x4_aruco_detector()

    input_video = cv2.VideoCapture(CAM_ID)

    while input_video.grab():
        ret, image = input_video.retrieve()
        if not ret:
            continue

        if not WIDTH or not HEIGHT:
            WIDTH, HEIGHT = image.shape[1], image.shape[0]

        # 复制图像用于绘制结果
        image_show = image.copy()

        # 检测标记并获取相关信息
        corners, ids = aruco_detect(aruco_detector, image, is_show=True)

        if ids is None:
            status = 0
            send_data = {
                "angle": 0,
                "distance": 0,
                "status": status
            }
        elif len(ids) == 2 and CAR_ARUCO_ID in ids and CTRL_ARUCO_ID in ids:
            status = 1
            # corners = corners[0]
            # ids = ids.flatten()
            # assert len(np.where(ids.flatten() == CAR_ARUCO_ID)[0]) < 2, f"CAR_ARUCO_ID: {CAR_ARUCO_ID} 最多只能出现1个"
            # print("ids:", ids)

            # 在图像上绘制检测到的标记
            cv2.aruco.drawDetectedMarkers(image_show, corners, ids)

            # print("===================")
            car_aruco_index = np.where(ids == CAR_ARUCO_ID)[0][0]
            car_corner = corners[int(car_aruco_index)]
            update_k(car_corner)

            send_data = {
                "left_speed": 0,
                "right_speed": 0,
                "status": 1
            }

            # print(send_data)

        else:
            status = 0
            send_data = {
                "angle": 0,
                "distance": 0,
                "status": status
            }

        json_data = json.dumps(send_data).encode()
        # print(json_data)
        try:
            if is_sendto_esp32 and ESP32_IP is not None and ESP32_PORT is not None:
                sock_udp.sendto(json_data, (ESP32_IP, ESP32_PORT))
        except OSError:
            pass

        cv2.imshow("out", image_show)
        # cv2.imshow("out_temp", image_circle)
        key = cv2.waitKey(1)
        if key == 27:  # esc 键退出
            break

    input_video.release()
    cv2.destroyAllWindows()
