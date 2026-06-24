from __future__ import annotations
from enum import Enum, auto

from gesture.recognizer import GestureType


class BodyAction(Enum):
    """
    用户身体动作的抽象描述，与具体手势识别实现解耦。
    英雄映射器只依赖此枚举，不直接依赖 gesture.recognizer。
    """
    LEFT_EXTEND       = auto()
    LEFT_RETRACT      = auto()
    RIGHT_EXTEND      = auto()
    RIGHT_RETRACT     = auto()
    LEFT_ZONE_TOP     = auto()
    LEFT_ZONE_MID     = auto()
    LEFT_ZONE_BOTTOM  = auto()
    RIGHT_ZONE_TOP    = auto()
    RIGHT_ZONE_MID    = auto()
    RIGHT_ZONE_BOTTOM = auto()
    BOTH_EXTEND       = auto()
    BOTH_RETRACT      = auto()
    BOTH_CROSS        = auto()
    SWIPE_LEFT        = auto()
    SWIPE_RIGHT       = auto()


# 修改此表即可重映射手势，无需改动任何英雄代码
GESTURE_TO_ACTION: dict[GestureType, BodyAction] = {
    GestureType.LEFT_EXTEND:       BodyAction.LEFT_EXTEND,
    GestureType.LEFT_RETRACT:      BodyAction.LEFT_RETRACT,
    GestureType.RIGHT_EXTEND:      BodyAction.RIGHT_EXTEND,
    GestureType.RIGHT_RETRACT:     BodyAction.RIGHT_RETRACT,
    GestureType.LEFT_ZONE_TOP:     BodyAction.LEFT_ZONE_TOP,
    GestureType.LEFT_ZONE_MID:     BodyAction.LEFT_ZONE_MID,
    GestureType.LEFT_ZONE_BOTTOM:  BodyAction.LEFT_ZONE_BOTTOM,
    GestureType.RIGHT_ZONE_TOP:    BodyAction.RIGHT_ZONE_TOP,
    GestureType.RIGHT_ZONE_MID:    BodyAction.RIGHT_ZONE_MID,
    GestureType.RIGHT_ZONE_BOTTOM: BodyAction.RIGHT_ZONE_BOTTOM,
    GestureType.BOTH_EXTEND:       BodyAction.BOTH_EXTEND,
    GestureType.BOTH_RETRACT:      BodyAction.BOTH_RETRACT,
    GestureType.BOTH_CROSS:        BodyAction.BOTH_CROSS,
    GestureType.SWIPE_LEFT:        BodyAction.SWIPE_LEFT,
    GestureType.SWIPE_RIGHT:       BodyAction.SWIPE_RIGHT,
}
