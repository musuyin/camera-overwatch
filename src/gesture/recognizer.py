from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
import time

from vision.hand_tracker import HandData
import config


class PositionZone(Enum):
    TOP    = auto()
    MID    = auto()
    BOTTOM = auto()


class Extension(Enum):
    EXTENDED  = auto()
    RETRACTED = auto()


class GestureType(Enum):
    LEFT_EXTEND        = auto()
    LEFT_RETRACT       = auto()
    RIGHT_EXTEND       = auto()
    RIGHT_RETRACT      = auto()
    LEFT_ZONE_TOP      = auto()
    LEFT_ZONE_MID      = auto()
    LEFT_ZONE_BOTTOM   = auto()
    RIGHT_ZONE_TOP     = auto()
    RIGHT_ZONE_MID     = auto()
    RIGHT_ZONE_BOTTOM  = auto()
    BOTH_EXTEND        = auto()
    BOTH_RETRACT       = auto()
    BOTH_CROSS         = auto()
    SWIPE_LEFT         = auto()
    SWIPE_RIGHT        = auto()


@dataclass
class GestureEvent:
    hand: str
    gesture_type: GestureType
    timestamp: float


@dataclass
class _HandState:
    handedness: str
    extension: Extension        = Extension.RETRACTED
    position_zone: PositionZone = PositionZone.MID
    stable_ext: int             = 0
    stable_zone: int            = 0
    last_fired_ext: Extension | None        = None
    last_fired_zone: PositionZone | None    = None
    wrist_x_history: deque = field(default_factory=lambda: deque(maxlen=config.SWIPE_FRAMES))
    prev_wrist_x: float | None  = None
    swipe_cooldown: int         = 0


class GestureRecognizer:
    """几何规则手势识别引擎，维护帧间状态，输出 GestureEvent 列表。"""

    def __init__(self, frame_width: int, frame_height: int):
        self._fw = frame_width
        self._fh = frame_height
        self._states: dict[str, _HandState] = {}
        self._prev_cross: bool | None = None
        self._cross_stable: int = 0

    def update(self, hand_data_list: list[HandData]) -> list[GestureEvent]:
        events: list[GestureEvent] = []
        present = {h.handedness for h in hand_data_list}

        for key in list(self._states.keys()):
            if key not in present:
                del self._states[key]

        for hd in hand_data_list:
            if hd.handedness not in self._states:
                self._states[hd.handedness] = _HandState(hd.handedness)
            events.extend(self._update_single_hand(hd))

        events.extend(self._check_both_extend())
        events.extend(self._check_cross(hand_data_list))

        return events

    def _update_single_hand(self, hd: HandData) -> list[GestureEvent]:
        st = self._states[hd.handedness]
        events: list[GestureEvent] = []
        side = hd.handedness

        # --- 伸缩 ---
        cur_ext = (
            Extension.EXTENDED if hd.palm_area > config.EXTEND_THRESHOLD
            else Extension.RETRACTED
        )
        if cur_ext == st.extension:
            st.stable_ext += 1
        else:
            st.stable_ext = 1
            st.extension = cur_ext

        if st.stable_ext == config.DEBOUNCE_FRAMES and cur_ext != st.last_fired_ext:
            st.last_fired_ext = cur_ext
            gt = (
                GestureType.LEFT_EXTEND  if side == "Left"  and cur_ext == Extension.EXTENDED  else
                GestureType.LEFT_RETRACT if side == "Left"  and cur_ext == Extension.RETRACTED else
                GestureType.RIGHT_EXTEND if side == "Right" and cur_ext == Extension.EXTENDED  else
                GestureType.RIGHT_RETRACT
            )
            events.append(self._make_event(side, gt))

        # --- 位置区域 ---
        wy = hd.wrist.y
        if wy < config.ZONE_TOP_BOUNDARY:
            cur_zone = PositionZone.TOP
        elif wy > config.ZONE_BOTTOM_BOUNDARY:
            cur_zone = PositionZone.BOTTOM
        else:
            cur_zone = PositionZone.MID

        if cur_zone == st.position_zone:
            st.stable_zone += 1
        else:
            st.stable_zone = 1
            st.position_zone = cur_zone

        if st.stable_zone == config.DEBOUNCE_FRAMES and cur_zone != st.last_fired_zone:
            st.last_fired_zone = cur_zone
            zone_map = {
                ("Left",  PositionZone.TOP):    GestureType.LEFT_ZONE_TOP,
                ("Left",  PositionZone.MID):    GestureType.LEFT_ZONE_MID,
                ("Left",  PositionZone.BOTTOM): GestureType.LEFT_ZONE_BOTTOM,
                ("Right", PositionZone.TOP):    GestureType.RIGHT_ZONE_TOP,
                ("Right", PositionZone.MID):    GestureType.RIGHT_ZONE_MID,
                ("Right", PositionZone.BOTTOM): GestureType.RIGHT_ZONE_BOTTOM,
            }
            events.append(self._make_event(side, zone_map[(side, cur_zone)]))

        # --- 甩手 ---
        wx = hd.wrist.x
        st.wrist_x_history.append(wx)
        if st.swipe_cooldown > 0:
            st.swipe_cooldown -= 1

        if len(st.wrist_x_history) >= 2 and st.swipe_cooldown == 0:
            dx = st.wrist_x_history[-1] - st.wrist_x_history[0]
            avg_vel = dx / max(len(st.wrist_x_history) - 1, 1)
            if abs(avg_vel) > config.SWIPE_MIN_VELOCITY:
                gt = GestureType.SWIPE_LEFT if avg_vel < 0 else GestureType.SWIPE_RIGHT
                events.append(self._make_event(side, gt))
                st.swipe_cooldown = config.SWIPE_FRAMES
                st.wrist_x_history.clear()

        st.prev_wrist_x = wx
        return events

    def _check_both_extend(self) -> list[GestureEvent]:
        if "Left" not in self._states or "Right" not in self._states:
            return []
        l_ext = self._states["Left"].last_fired_ext
        r_ext = self._states["Right"].last_fired_ext
        l_just = self._states["Left"].stable_ext  == config.DEBOUNCE_FRAMES
        r_just = self._states["Right"].stable_ext == config.DEBOUNCE_FRAMES
        if (l_just or r_just) and l_ext == Extension.EXTENDED and r_ext == Extension.EXTENDED:
            return [self._make_event("Both", GestureType.BOTH_EXTEND)]
        if (l_just or r_just) and l_ext == Extension.RETRACTED and r_ext == Extension.RETRACTED:
            return [self._make_event("Both", GestureType.BOTH_RETRACT)]
        return []

    def _check_cross(self, hand_data_list: list[HandData]) -> list[GestureEvent]:
        left_data  = next((h for h in hand_data_list if h.handedness == "Left"),  None)
        right_data = next((h for h in hand_data_list if h.handedness == "Right"), None)
        if left_data is None or right_data is None:
            self._prev_cross = None
            self._cross_stable = 0
            return []

        is_cross = left_data.wrist.x > right_data.wrist.x

        if is_cross == self._prev_cross:
            self._cross_stable += 1
        else:
            self._cross_stable = 1
            self._prev_cross = is_cross

        if self._cross_stable == config.DEBOUNCE_FRAMES and is_cross:
            self._cross_stable += 1
            return [self._make_event("Both", GestureType.BOTH_CROSS)]
        return []

    @staticmethod
    def _make_event(hand: str, gesture_type: GestureType) -> GestureEvent:
        return GestureEvent(hand, gesture_type, time.monotonic() * 1000)
