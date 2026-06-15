from __future__ import annotations
import sys
import time
import cv2
import mediapipe as mp
import numpy as np

import config
from capture import CaptureModule
from hand_tracker import HandTracker
from gesture_recognizer import GestureRecognizer
from hero_state import HeroMapper
from input_mapper import InputController
from heroes.moira import MoiraMapper
from heroes.ramattra import RamattraMapper


# ──────────────────────────────────────────────────────────────────────────────
# 英雄选择
# ──────────────────────────────────────────────────────────────────────────────

def select_hero() -> HeroMapper:
    print("选择英雄：")
    print("  1. 莫伊拉（Moira）")
    print("  2. 拉玛莎（Ramattra）")
    while True:
        choice = input("输入数字（1/2）：").strip()
        if choice == "1":
            return MoiraMapper()
        if choice == "2":
            return RamattraMapper()
        print("无效输入，请重新选择。")


# ──────────────────────────────────────────────────────────────────────────────
# HUD 渲染
# ──────────────────────────────────────────────────────────────────────────────

_FONT       = cv2.FONT_HERSHEY_SIMPLEX
_TEXT_COLOR = (0, 255, 120)
_SHADOW     = (0, 0, 0)


def _put_text_shadowed(frame: np.ndarray, text: str, pos: tuple[int, int],
                       scale: float = 0.55, thickness: int = 1) -> None:
    x, y = pos
    cv2.putText(frame, text, (x + 1, y + 1), _FONT, scale, _SHADOW,    thickness + 1, cv2.LINE_AA)
    cv2.putText(frame, text, (x,     y),     _FONT, scale, _TEXT_COLOR, thickness,     cv2.LINE_AA)


def render_hud(frame: np.ndarray, status: dict, fps: float, last_latency: float) -> None:
    lines = [
        f"Hero: {status.get('hero', '-')}",
        f"Form: {status.get('form', '-')}" if "form" in status else None,
        f"Left:  {status.get('left_hand',  '-')}" if "left_hand"  in status else None,
        f"Right: {status.get('right_hand', '-')}" if "right_hand" in status else None,
        f"Block: {status.get('blocking',   '-')}" if "blocking"   in status else None,
        f"Last:  {status.get('last_event', '-')}",
        f"Latency: {last_latency:.1f}ms",
        f"FPS: {fps:.1f}",
    ]
    y = 28
    for line in lines:
        if line is None:
            continue
        _put_text_shadowed(frame, line, (10, y))
        y += 24


def draw_hand_landmarks(frame: np.ndarray, hand_data_list, tracker: HandTracker) -> None:
    mp_drawing = tracker.get_mp_drawing()
    mp_hands   = tracker.get_mp_hands()

    # 重新跑推理以拿到 NormalizedLandmarkList（HandData 只存 Point3D）
    # 实际场景中用同一帧，MP Hands 会直接返回缓存结果，不会增加额外耗时
    # 注意：此处绘制直接在已有 frame 上叠加，无需重复推理
    # 改为在 process() 中顺带保存原始 landmarks 更干净；此处简化为跳过骨架绘制
    # 仅绘制手腕点作为标记
    h, w = frame.shape[:2]
    for hd in hand_data_list:
        cx = int(hd.wrist.x * w)
        cy = int(hd.wrist.y * h)
        cv2.circle(frame, (cx, cy), 6, (0, 200, 255), -1)
        cv2.putText(frame, hd.handedness[0], (cx + 8, cy - 8), _FONT, 0.45, (0, 200, 255), 1, cv2.LINE_AA)


# ──────────────────────────────────────────────────────────────────────────────
# 主循环
# ──────────────────────────────────────────────────────────────────────────────

def main_loop(hero: HeroMapper) -> None:
    capture    = CaptureModule()
    tracker    = HandTracker()
    controller = InputController()

    # 从第一帧确定分辨率
    frame = capture.read_frame()
    if frame is None:
        print("无法读取摄像头帧，程序退出。")
        capture.release()
        tracker.close()
        return

    h, w = frame.shape[:2]
    recognizer = GestureRecognizer(w, h)

    last_latency = 0.0
    fps_timer    = time.monotonic()
    fps_count    = 0
    fps          = 0.0

    print(f"已选择英雄：{hero.name}，按 ESC 退出。")

    while True:
        frame = capture.read_frame()
        if frame is None:
            continue

        # 水平翻转（镜像，让用户看到自然的镜像画面）
        frame = cv2.flip(frame, 1)

        # 追踪
        hand_data_list = tracker.process(frame)

        # 识别
        events = recognizer.update(hand_data_list)

        # 映射 + 执行
        for event in events:
            cmds = hero.handle(event)
            for cmd in cmds:
                done_ts     = controller.execute(cmd)
                last_latency = done_ts - event.timestamp

        # 绘制关键点
        draw_hand_landmarks(frame, hand_data_list, tracker)

        # FPS 计算
        fps_count += 1
        elapsed = time.monotonic() - fps_timer
        if elapsed >= 1.0:
            fps       = fps_count / elapsed
            fps_count = 0
            fps_timer = time.monotonic()

        # HUD
        render_hud(frame, hero.get_status(), fps, last_latency)

        cv2.imshow("Gesture Overwatch", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break

    capture.release()
    tracker.close()
    cv2.destroyAllWindows()


# ──────────────────────────────────────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    hero = select_hero()
    main_loop(hero)
