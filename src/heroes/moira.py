from __future__ import annotations
from pynput.mouse import Button

from gesture.body_action import BodyAction
from heroes.base import HeroMapper, make_cmd
from input.controller import CommandAction, GameCommand


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
        self._left_pressing   = False
        self._right_pressing  = False
        self._last_action_name = "-"

    def handle(self, action: BodyAction, timestamp: float) -> list[GameCommand]:
        self._last_action_name = action.name
        handler = self._BINDINGS.get(action)
        return handler(self, timestamp) if handler else []

    def _left_extend(self, ts: float) -> list[GameCommand]:
        if self._left_pressing:
            return []
        self._left_pressing = True
        return [make_cmd(CommandAction.MOUSE_DOWN, Button.left, ts)]

    def _left_retract(self, ts: float) -> list[GameCommand]:
        if not self._left_pressing:
            return []
        self._left_pressing = False
        return [make_cmd(CommandAction.MOUSE_UP, Button.left, ts)]

    def _right_extend(self, ts: float) -> list[GameCommand]:
        if self._right_pressing:
            return []
        self._right_pressing = True
        return [make_cmd(CommandAction.MOUSE_DOWN, Button.right, ts)]

    def _right_retract(self, ts: float) -> list[GameCommand]:
        if not self._right_pressing:
            return []
        self._right_pressing = False
        return [make_cmd(CommandAction.MOUSE_UP, Button.right, ts)]

    def _throw(self, ts: float) -> list[GameCommand]:
        return [make_cmd(CommandAction.KEY_DOWN, 'e', ts), make_cmd(CommandAction.KEY_UP, 'e', ts)]

    def _ultimate(self, ts: float) -> list[GameCommand]:
        return [make_cmd(CommandAction.KEY_DOWN, 'q', ts), make_cmd(CommandAction.KEY_UP, 'q', ts)]

    _BINDINGS: dict = {
        BodyAction.LEFT_EXTEND:   _left_extend,
        BodyAction.LEFT_RETRACT:  _left_retract,
        BodyAction.RIGHT_EXTEND:  _right_extend,
        BodyAction.RIGHT_RETRACT: _right_retract,
        BodyAction.SWIPE_LEFT:    _throw,
        BodyAction.SWIPE_RIGHT:   _throw,
        BodyAction.BOTH_EXTEND:   _ultimate,
    }

    def get_status(self) -> dict:
        return {
            "hero":        self.name,
            "left_hand":   "EXTENDING" if self._left_pressing  else "retracted",
            "right_hand":  "EXTENDING" if self._right_pressing else "retracted",
            "last_action": self._last_action_name,
        }
