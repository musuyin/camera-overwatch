from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import cv2
import mediapipe as mp
import numpy as np

# ── 模型文件 ──────────────────────────────────────────────────────────────────
MODEL_FILENAME = "hand_landmarker.task"
_MODEL_PATH    = Path(__file__).parent / MODEL_FILENAME


def _ensure_model() -> str:
    if not _MODEL_PATH.exists():
        raise FileNotFoundError(
            f"找不到模型文件：{_MODEL_PATH}\n"
            f"请先运行：python setup_model.py"
        )
    return str(_MODEL_PATH)


# ── 数据类 ────────────────────────────────────────────────────────────────────

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


# ── 面积计算 ──────────────────────────────────────────────────────────────────

def _cross2d(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx


def _quad_area(pts: list[tuple[float, float]]) -> float:
    n = len(pts)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += _cross2d(pts[i][0], pts[i][1], pts[j][0], pts[j][1])
    return abs(area) * 0.5


# ── HandTracker ───────────────────────────────────────────────────────────────

_HandLandmarker        = mp.tasks.vision.HandLandmarker
_HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
_RunningMode           = mp.tasks.vision.RunningMode
_BaseOptions           = mp.tasks.BaseOptions

# 用于面积估算的四个关键点索引：手腕、食指根、中指根、小指根
_PALM_IDX = (0, 5, 9, 17)


class HandTracker:
    """封装 MediaPipe Tasks HandLandmarker，输出 HandData 列表。"""

    def __init__(self, max_hands: int = 2):
        model_path = _ensure_model()
        options = _HandLandmarkerOptions(
            base_options=_BaseOptions(model_asset_path=model_path),
            running_mode=_RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = _HandLandmarker.create_from_options(options)
        self._frame_w = 1
        self._frame_h = 1
        self._timestamp_ms = 0

    def process(self, bgr_frame: np.ndarray) -> list[HandData]:
        self._frame_h, self._frame_w = bgr_frame.shape[:2]
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        self._timestamp_ms += 1  # 单调递增时间戳（VIDEO 模式要求）
        result = self._landmarker.detect_for_video(mp_image, self._timestamp_ms)

        hand_data_list: list[HandData] = []
        if not result.hand_landmarks:
            return hand_data_list

        for lm_list, handedness_list in zip(result.hand_landmarks, result.handedness):
            label = handedness_list[0].category_name  # "Left" 或 "Right"
            lms = [Point3D(lm.x, lm.y, lm.z) for lm in lm_list]
            wrist = lms[0]
            palm_pts = [
                (lms[i].x * self._frame_w, lms[i].y * self._frame_h)
                for i in _PALM_IDX
            ]
            area = _quad_area(palm_pts)
            hand_data_list.append(HandData(label, lms, wrist, area))

        return hand_data_list

    def close(self):
        self._landmarker.close()

    # main.py 中只用到这两个方法供 draw_hand_landmarks 调用，保留接口兼容
    def get_mp_drawing(self):
        return None

    def get_mp_hands(self):
        return None
