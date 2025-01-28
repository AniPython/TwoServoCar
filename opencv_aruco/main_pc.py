import socket
import json
from typing import Tuple

import cv2
import numpy as np
import time

from consts import *

status = 0  # 0: 无发现 car corner 或圆形, 1: 有发现 car corner 和 圆形
k = 1  # 屏幕像素与毫米的比例系数  px / mm
is_sendto_esp32 = True
sock_udp = None
image_show = None
WIDTH = None  # 屏幕宽度
HEIGHT = None  # 屏幕高度
car_center = (0, 0)


def calculate_center(corner: np.typing.ArrayLike) -> Tuple[int, int]:
    """返回中点"""
    center_x = np.mean(corner[:, 0])
    center_y = np.mean(corner[:, 1])
    return int(center_x), int(center_y)


def get_corner_edge_length(corner: np.typing.ArrayLike) -> float:
    corner = corner.squeeze()
    return np.sqrt(np.square(corner[0][0] - corner[1][0]) + np.square(corner[0][1] - corner[1][1]))


def update_k(car_corner: np.typing.ArrayLike):
    global k
    # 获取 car_corner 的边长
    edge_length = get_corner_edge_length(car_corner)
    # print("edge_length_px: ", edge_length)
    k = edge_length / CAR_ARUCO_SIZE_MM


def radians_to_degrees(rad: float) -> float:
    deg = np.degrees(rad)
    if deg > 180:
        deg -= 360
    elif deg < -180:
        deg += 360
    return deg


def move_to(corner, coordinate, keep_distance_px=0, keep_radians=None, is_show=False) -> Tuple[float, float]:
    """
    以 aruco 中心点作为锚点, 把小车移动到指定的坐标位置
    :param is_show: 画出
    :param corner: ArucoDetector.detectMarkers 返回的 corners[0]
    :param coordinate: 期望移动到的屏幕坐标
    :param keep_distance_px: 跟目标保持这个距离
    :param keep_radians: 保持这个弧度, 相对于屏幕的坐标
    :return: 角度 和 毫米距离
    """
    global car_center

    corner = corner.squeeze()

    # 计算 ArUco 标记的中心点
    center_x, center_y = calculate_center(corner)
    car_center = (center_x, center_y)

    # 获取直线1的中点
    car_line1_center = calculate_center(corner[0:2])

    # car 与 目标点向量
    target_vector = np.array(coordinate) - np.array([center_x, center_y])

    # car 自身的向量
    car_vector = np.array(car_line1_center) - np.array([center_x, center_y])

    # 目标点的距离和角度
    target_distance_px = np.linalg.norm(target_vector)
    target_angle_rad = np.arctan2(target_vector[1], target_vector[0]) - np.arctan2(car_vector[1], car_vector[0])

    # 如果需要保持特定的角度
    if keep_radians is not None:
        target_angle_rad -= keep_radians  # 调整目标角度

    # 如果需要保持特定的距离
    if keep_distance_px and keep_distance_px >= 0:
        target_distance_px -= keep_distance_px

    # 转换角度为度数
    target_angle_deg = radians_to_degrees(target_angle_rad)

    if is_show:
        cv2.line(image_show, [center_x, center_y], car_line1_center, (20, 240, 20), 3)

    # 返回角度和距离
    return target_angle_deg, target_distance_px / k


def circle_detect(
        image,
        min_dist=100,
        param1=45,
        param2=60,
        min_radius=10,
        max_radius=60,
        is_draw=False
):
    global image_show
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image = cv2.medianBlur(image, 5)

    hough_circles = cv2.HoughCircles(
        image, cv2.HOUGH_GRADIENT, dp=1.2, minDist=min_dist,
        param1=param1, param2=param2, minRadius=min_radius, maxRadius=max_radius
    )
    if is_draw and hough_circles is not None:
        circles = np.round(hough_circles[0, :]).astype("int")
        for (x, y, r) in circles:
            cv2.circle(image_show, (x, y), r, (0, 255, 0), 2)
            cv2.rectangle(image_show, (x - 5, y - 5), (x + 5, y + 5), (0, 128, 255), -1)
            cv2.putText(image_show, f"R={r}", (x - r, y - r - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    return hough_circles


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


def default_4x4_aruco_detector():
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_250)
    detector_params = cv2.aruco.DetectorParameters()
    return cv2.aruco.ArucoDetector(dictionary, detector_params)

def find_nearest_corner_center(corner, corners, is_show=False):
    """
    :return: (x, y)
    """
    global image_show
    corner = corner.squeeze()
    # print(f"{corners=}")
    # corners = corners[0]
    corner_center = calculate_center(corner)

    # 获取所有 corners 的中心
    corners_center = np.array([calculate_center(corner.squeeze()) for corner in corners])

    distances = np.sqrt(np.sum((corners_center[:, 0:2] - np.array(corner_center)) ** 2, axis=1))

    # 找到距离最近的那个点的索引
    nearest_index = np.argmin(distances)

    # 获取最近点的坐标和半径
    nearest_center = corners_center[nearest_index]
    x, y = (int(nearest_center[0]), int(nearest_center[1]))

    if is_show:
        cv2.circle(image_show, (x, y), 8, (30, 30, 200), -1)
        cv2.line(image_show, corner_center, (x, y), (30, 30, 200), 3)

    return x, y


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

        # 用于检测圆, 四边 SAVE_AREA_PX 范围变成空白, 只留中间区域
        # image_circle = image.copy()
        # image_circle[:SAVE_AREA_PX, :] = 0  # 上
        # image_circle[HEIGHT - SAVE_AREA_PX:, :] = 0  # 下
        # image_circle[:, :SAVE_AREA_PX] = 0  # 左
        # image_circle[:, WIDTH - SAVE_AREA_PX:] = 0  # 右

        # 检测标记并获取相关信息
        corners, ids = aruco_detect(aruco_detector, image, is_show=True)

        if ids is None:
            status = 0
            send_data = {
                "angle": 0,
                "distance": 0,
                "status": status
            }
        elif len(ids) >= 2:
            status = 1
            # corners = corners[0]
            # ids = ids.flatten()
            assert len(np.where(ids.flatten() == CAR_ARUCO_ID)[0]) < 2, f"CAR_ARUCO_ID: {CAR_ARUCO_ID} 最多只能出现1个"
            # print("ids:", ids)

            # 在图像上绘制检测到的标记
            cv2.aruco.drawDetectedMarkers(image_show, corners, ids)

            if CAR_ARUCO_ID in ids:
                # print("===================")
                car_aruco_index = np.where(ids == CAR_ARUCO_ID)[0][0]
                car_corner = corners[int(car_aruco_index)]
                update_k(car_corner)

                # corners 排除 ids == CAR_ARUCO_ID
                corners_goods = np.delete(np.array(corners), np.where(ids.flatten() == CAR_ARUCO_ID), axis=0)
                # print(f"{corners_goods=}")

                x, y = find_nearest_corner_center(car_corner, corners_goods, is_show=True)
                # print(x, y, r)
                # print("**************")

                angle_deg, distance_mm = move_to(car_corner, (x, y), is_show=True)

                # time.sleep(0.5)

                send_data = {
                    "angle": angle_deg,
                    "distance": distance_mm,
                    "status": 1
                }

                # print(send_data)

            else:
                send_data = {
                    "angle": 0,
                    "distance": 0,
                    "status": 1
                }
                json_data = json.dumps(send_data).encode()
                try:
                    if is_sendto_esp32 and ESP32_IP is not None and ESP32_PORT is not None:
                        sock_udp.sendto(json_data, (ESP32_IP, ESP32_PORT))
                except OSError:
                    pass

        elif len(ids) == 1 and CAR_ARUCO_ID in ids:
            status = 2
            angle_deg, distance_mm = move_to(corners[0], GOAL_POINT, is_show=True)
            send_data = {
                "angle": angle_deg,
                "distance": distance_mm,
                "status": status
            }

        else:
            status = 0
            send_data = {
                "angle": 0,
                "distance": 0,
                "status": status
            }

        if abs(send_data['distance']) < MIN_DISTANCE_PX:
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

        if status == 2:
            cv2.circle(image_show, GOAL_POINT, 12, (50, 180, 50), -1)  # 画目标点
            cv2.line(image_show, car_center, GOAL_POINT, (20, 240, 20), 3)
        cv2.imshow("out", image_show)
        # cv2.imshow("out_temp", image_circle)
        key = cv2.waitKey(1)
        if key == 27:  # esc 键退出
            break

    input_video.release()
    cv2.destroyAllWindows()


def test_move_to():
    global image_show, sock_udp

    sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 创建ArUco探测器对象
    aruco_detector = default_4x4_aruco_detector()

    input_video = cv2.VideoCapture(CAM_ID)

    while input_video.grab():
        ret, image = input_video.retrieve()
        if not ret:
            continue

        # 复制图像用于绘制结果
        image_show = image.copy()

        # 检测标记并获取相关信息
        corners, ids = aruco_detect(aruco_detector, image, is_show=False)

        if ids is not None and len(ids) > 0:
            # 在图像上绘制检测到的标记
            cv2.aruco.drawDetectedMarkers(image_show, corners, ids)

            if CAR_ARUCO_ID in ids:
                car_aruco_index = np.where(ids == CAR_ARUCO_ID)[0][0]
                car_corner = corners[int(car_aruco_index)]
                update_k(car_corner)

                angle, distance = move_to(car_corner, GOAL_POINT, is_show=True)
                # print("angle: ", angle)
                # print("distance: ", distance)
                sock_udp.sendto(
                    json.dumps({"angle": angle, "distance": distance, "status": 1}).encode(),
                    (ESP32_IP, ESP32_PORT)
                )
                # time.sleep(0.5)

        cv2.circle(image_show, GOAL_POINT, 12, (50, 180, 50), -1)  # 画目标点
        cv2.imshow("out", image_show)
        key = cv2.waitKey(1)
        if key == 27:  # esc 键退出
            break

    input_video.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
    # test_move_to()
