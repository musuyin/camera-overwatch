from __future__ import annotations
from enum import Enum, auto
from pynput.keyboard import Key
from pynput.mouse import Button

from gesture.body_action import BodyAction
from heroes.base import HeroMapper
from input.controller import CommandAction, GameCommand


class FormState(Enum):
    OMNIC   = auto()
    NEMESIS = auto()


def _cmd(action: CommandAction, key, ts: float) -> GameCommand:
    return GameCommand(action, key, ts)


class RamattraMapper(HeroMapper):
    """
    拉玛莎（Ramattra）：位置区域 + 形态切换状态机型。

    普通形态（OMNIC）：
      右手伸出   → 普攻（左键点击）
      右手区域上 → 立盾（Shift 按住）
      右手区域中/下 → 释放盾；区域下额外触发 E
      双手交叉   → 变身天罚形态（Q）

    天罚形态（NEMESIS）：
      右手伸出   → 右拳（左键点击）
      左手伸出   → 左拳（右键点击）
      双手同时伸出 → 格挡（Shift 按住）
      双手同时收回 → 释放格挡
      双手交叉   → 退出天罚形态
    """

    @property
    def name(self) -> str:
        return "Ramattra"

    def __init__(self):
        self._form             = FormState.OMNIC
        self._blocking         = False
        self._last_action_name = "-"

    def handle(self, action: BodyAction, timestamp: float) -> list[GameCommand]:
        self._last_action_name = action.name
        table = self._OMNIC_BINDINGS if self._form == FormState.OMNIC else self._NEMESIS_BINDINGS
        handler = table.get(action)
        return handler(self, timestamp) if handler else []

    def _omnic_attack(self, ts: float) -> list[GameCommand]:
        return [_cmd(CommandAction.MOUSE_DOWN, Button.left, ts),
                _cmd(CommandAction.MOUSE_UP,   Button.left, ts)]

    def _omnic_shield_on(self, ts: float) -> list[GameCommand]:
        if self._blocking:
            return []
        self._blocking = True
        return [_cmd(CommandAction.KEY_DOWN, Key.shift, ts)]

    def _omnic_shield_off(self, ts: float) -> list[GameCommand]:
        if not self._blocking:
            return []
        self._blocking = False
        return [_cmd(CommandAction.KEY_UP, Key.shift, ts)]

    def _omnic_vortex(self, ts: float) -> list[GameCommand]:
        cmds = self._omnic_shield_off(ts)
        cmds += [_cmd(CommandAction.KEY_DOWN, 'e', ts), _cmd(CommandAction.KEY_UP, 'e', ts)]
        return cmds

    def _omnic_transform(self, ts: float) -> list[GameCommand]:
        self._form = FormState.NEMESIS
        return [_cmd(CommandAction.KEY_DOWN, 'q', ts), _cmd(CommandAction.KEY_UP, 'q', ts)]

    def _nemesis_right_punch(self, ts: float) -> list[GameCommand]:
        return [_cmd(CommandAction.MOUSE_DOWN, Button.left, ts),
                _cmd(CommandAction.MOUSE_UP,   Button.left, ts)]

    def _nemesis_left_punch(self, ts: float) -> list[GameCommand]:
        return [_cmd(CommandAction.MOUSE_DOWN, Button.right, ts),
                _cmd(CommandAction.MOUSE_UP,   Button.right, ts)]

    def _nemesis_block_on(self, ts: float) -> list[GameCommand]:
        if self._blocking:
            return []
        self._blocking = True
        return [_cmd(CommandAction.KEY_DOWN, Key.shift, ts)]

    def _nemesis_block_off(self, ts: float) -> list[GameCommand]:
        if not self._blocking:
            return []
        self._blocking = False
        return [_cmd(CommandAction.KEY_UP, Key.shift, ts)]

    def _nemesis_exit(self, ts: float) -> list[GameCommand]:
        cmds = self._nemesis_block_off(ts)
        self._form = FormState.OMNIC
        return cmds

    _OMNIC_BINDINGS: dict = {
        BodyAction.RIGHT_EXTEND:      _omnic_attack,
        BodyAction.RIGHT_ZONE_TOP:    _omnic_shield_on,
        BodyAction.RIGHT_ZONE_MID:    _omnic_shield_off,
        BodyAction.RIGHT_ZONE_BOTTOM: _omnic_vortex,
        BodyAction.BOTH_CROSS:        _omnic_transform,
    }

    _NEMESIS_BINDINGS: dict = {
        BodyAction.RIGHT_EXTEND:  _nemesis_right_punch,
        BodyAction.LEFT_EXTEND:   _nemesis_left_punch,
        BodyAction.BOTH_EXTEND:   _nemesis_block_on,
        BodyAction.BOTH_RETRACT:  _nemesis_block_off,
        BodyAction.BOTH_CROSS:    _nemesis_exit,
    }

    def get_status(self) -> dict:
        return {
            "hero":        self.name,
            "form":        self._form.name,
            "blocking":    self._blocking,
            "last_action": self._last_action_name,
        }
