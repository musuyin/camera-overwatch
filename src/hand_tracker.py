from __future__ import annotations
from dataclasses import dataclass
import math
import cv2
import mediapipe as mp
import numpy as np


@dataclass
class Point3D:
    x: float
    y: float
    z: float


@dataclass
class HandData:
    handedness: str          # "Left" 或 "Right"
    landmarks: list[Point3D]
    wrist: Point3D           # landmarks[0] 的快捷引用
    palm_area: float         # 手掌四边形面积（像素²）


def _cross2d(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx


def _quad_area(pts: list[tuple[float, float]]) -> float:
    """四边形面积（向量叉积法，pts 按顺序排列）。"""
    n = len(pts)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += _cross2d(pts[i][0], pts[i][1], pts[j][0], pts[j][1])
    return abs(area) * 0.5


class HandTracker:
    """封装 MediaPipe Hands，输出 HandData 列表。"""

    # 用于面积估算的四个关键点索引：手腕、食指根、中指根、小指根
    _PALM_IDX = (0, 5, 9, 17)

    def __init__(self, max_hands: int = 2):
        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        )
        self._mp_drawing = mp.solutions.drawing_utils
        self._mp_drawing_styles = mp.solutions.drawing_styles
        self._frame_w = 1
        self._frame_h = 1

    def process(self, bgr_frame: np.ndarray) -> list[HandData]:
        self._frame_h, self._frame_w = bgr_frame.shape[:2]
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)

        hand_data_list: list[HandData] = []
        if not results.multi_hand_landmarks:
            return hand_data_list

        for hand_lms, hand_info in zip(
            results.multi_hand_landmarks, results.multi_handedness
        ):
            label = hand_info.classification[0].label  # "Left" 或 "Right"
            lms = [
                Point3D(lm.x, lm.y, lm.z)
                for lm in hand_lms.landmark
            ]
            wrist = lms[0]
            palm_pts = [
                (lms[i].x * self._frame_w, lms[i].y * self._frame_h)
                for i in self._PALM_IDX
            ]
            area = _quad_area(palm_pts)
            hand_data_list.append(HandData(label, lms, wrist, area))

        return hand_data_list

    def draw_landmarks(self, bgr_frame: np.ndarray, bgr_result_frame: np.ndarray) -> None:
        """在已有帧上绘制关键点（仅供 HUDRenderer 调用）。"""
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        if results.multi_hand_landmarks:
            for hand_lms in results.multi_hand_landmarks:
                self._mp_drawing.draw_landmarks(
                    bgr_result_frame,
                    hand_lms,
                    self._mp_hands.HAND_CONNECTIONS,
                    self._mp_drawing_styles.get_default_hand_landmarks_style(),
                    self._mp_drawing_styles.get_default_hand_connections_style(),
                )

    def get_mp_drawing(self):
        return self._mp_drawing

    def get_mp_hands(self):
        return self._mp_hands

    def close(self):
        self._hands.close()
