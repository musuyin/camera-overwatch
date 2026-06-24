import cv2
import numpy as np
import config


class CaptureModule:
    def __init__(self, camera_id: int = config.CAMERA_ID, target_fps: int = config.TARGET_FPS):
        self._cap = cv2.VideoCapture(camera_id)
        if not self._cap.isOpened():
            raise RuntimeError(f"无法打开摄像头（ID={camera_id}）")
        self._cap.set(cv2.CAP_PROP_FPS, target_fps)

    def read_frame(self) -> np.ndarray | None:
        ret, frame = self._cap.read()
        if not ret:
            return None
        return frame  # BGR

    def release(self):
        self._cap.release()
