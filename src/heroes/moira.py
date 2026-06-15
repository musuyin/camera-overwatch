from __future__ import annotations
from pynput.mouse import Button

from gesture_recognizer import GestureEvent, GestureType
from hero_state import HeroMapper
from input_mapper import CommandAction, GameCommand


def _cmd(action: CommandAction, key, event: GestureEvent) -> GameCommand:
    return GameCommand(action, key, event)


class MoiraMapper(HeroMapper):
    """
    莫伊拉（Moira）：双手独立状态型。

    左手伸出 → 左键按住（治疗光束）
    右手伸出 → 右键按住（伤害光束）
    甩手    → E（扔球）
    双手同时伸出 → Q（大招）
    """

    @property
    def name(self) -> str:
        return "Moira"

    def __init__(self):
        self._left_pressing  = False
        self._right_pressing = False
        self._last_event_name = "-"

    def handle(self, event: GestureEvent) -> list[GameCommand]:
        gt = event.gesture_type
        cmds: list[GameCommand] = []
        self._last_event_name = gt.name

        if gt == GestureType.LEFT_EXTEND and not self._left_pressing:
            cmds.append(_cmd(CommandAction.MOUSE_DOWN, Button.left, event))
            self._left_pressing = True

        elif gt == GestureType.LEFT_RETRACT and self._left_pressing:
            cmds.append(_cmd(CommandAction.MOUSE_UP, Button.left, event))
            self._left_pressing = False

        elif gt == GestureType.RIGHT_EXTEND and not self._right_pressing:
            cmds.append(_cmd(CommandAction.MOUSE_DOWN, Button.right, event))
            self._right_pressing = True

        elif gt == GestureType.RIGHT_RETRACT and self._right_pressing:
            cmds.append(_cmd(CommandAction.MOUSE_UP, Button.right, event))
            self._right_pressing = False

        elif gt in (GestureType.SWIPE_LEFT, GestureType.SWIPE_RIGHT):
            cmds.append(_cmd(CommandAction.KEY_DOWN, 'e', event))
            cmds.append(_cmd(CommandAction.KEY_UP,   'e', event))

        elif gt == GestureType.BOTH_EXTEND:
            cmds.append(_cmd(CommandAction.KEY_DOWN, 'q', event))
            cmds.append(_cmd(CommandAction.KEY_UP,   'q', event))

        return cmds

    def get_status(self) -> dict:
        return {
            "hero":        self.name,
            "left_hand":   "EXTENDING" if self._left_pressing  else "retracted",
            "right_hand":  "EXTENDING" if self._right_pressing else "retracted",
            "last_event":  self._last_event_name,
        }
