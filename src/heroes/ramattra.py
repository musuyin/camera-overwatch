from __future__ import annotations
from enum import Enum, auto
from pynput.keyboard import Key
from pynput.mouse import Button

from gesture_recognizer import GestureEvent, GestureType
from hero_state import HeroMapper
from input_mapper import CommandAction, GameCommand


class FormState(Enum):
    OMNIC   = auto()
    NEMESIS = auto()


def _cmd(action: CommandAction, key, event: GestureEvent) -> GameCommand:
    return GameCommand(action, key, event)


class RamattraMapper(HeroMapper):
    """
    拉玛莎（Ramattra）：位置区域 + 形态切换状态机型。

    普通形态（OMNIC）：
      右手伸出（中区）→ 普攻（左键点击）
      右手抬至上区   → 立盾（Shift 按住）
      右手离开上区   → 释放盾（Shift 松开）
      右手压至下区   → 丢漩涡（E）
      双手交叉       → 变身天罚形态（Q）

    天罚形态（NEMESIS）：
      右手伸出       → 右拳（左键点击）
      左手伸出       → 左拳（右键点击）
      双手同时伸出   → 格挡（Shift 按住）
      双手同时收回   → 释放格挡（Shift 松开）
      双手交叉       → 退出天罚形态（无额外按键）
    """

    @property
    def name(self) -> str:
        return "Ramattra"

    def __init__(self):
        self._form   = FormState.OMNIC
        self._blocking = False
        self._last_event_name = "-"

    def handle(self, event: GestureEvent) -> list[GameCommand]:
        gt = event.gesture_type
        cmds: list[GameCommand] = []
        self._last_event_name = gt.name

        # 形态切换（两种形态通用）
        if gt == GestureType.BOTH_CROSS:
            if self._form == FormState.OMNIC:
                self._form = FormState.NEMESIS
                cmds.append(_cmd(CommandAction.KEY_DOWN, 'q', event))
                cmds.append(_cmd(CommandAction.KEY_UP,   'q', event))
            else:
                # 退出天罚形态，确保 Shift 释放
                if self._blocking:
                    cmds.append(_cmd(CommandAction.KEY_UP, Key.shift, event))
                    self._blocking = False
                self._form = FormState.OMNIC
            return cmds

        if self._form == FormState.OMNIC:
            cmds.extend(self._handle_omnic(event))
        else:
            cmds.extend(self._handle_nemesis(event))

        return cmds

    def _handle_omnic(self, event: GestureEvent) -> list[GameCommand]:
        gt = event.gesture_type
        cmds: list[GameCommand] = []

        if gt == GestureType.RIGHT_EXTEND:
            cmds.append(_cmd(CommandAction.MOUSE_DOWN, Button.left,  event))
            cmds.append(_cmd(CommandAction.MOUSE_UP,   Button.left,  event))

        elif gt == GestureType.RIGHT_ZONE_TOP:
            if not self._blocking:
                cmds.append(_cmd(CommandAction.KEY_DOWN, Key.shift, event))
                self._blocking = True

        elif gt in (GestureType.RIGHT_ZONE_MID, GestureType.RIGHT_ZONE_BOTTOM):
            if self._blocking:
                cmds.append(_cmd(CommandAction.KEY_UP, Key.shift, event))
                self._blocking = False
            if gt == GestureType.RIGHT_ZONE_BOTTOM:
                cmds.append(_cmd(CommandAction.KEY_DOWN, 'e', event))
                cmds.append(_cmd(CommandAction.KEY_UP,   'e', event))

        return cmds

    def _handle_nemesis(self, event: GestureEvent) -> list[GameCommand]:
        gt = event.gesture_type
        cmds: list[GameCommand] = []

        if gt == GestureType.RIGHT_EXTEND:
            cmds.append(_cmd(CommandAction.MOUSE_DOWN, Button.left,  event))
            cmds.append(_cmd(CommandAction.MOUSE_UP,   Button.left,  event))

        elif gt == GestureType.LEFT_EXTEND:
            cmds.append(_cmd(CommandAction.MOUSE_DOWN, Button.right, event))
            cmds.append(_cmd(CommandAction.MOUSE_UP,   Button.right, event))

        elif gt == GestureType.BOTH_EXTEND:
            if not self._blocking:
                cmds.append(_cmd(CommandAction.KEY_DOWN, Key.shift, event))
                self._blocking = True

        elif gt == GestureType.BOTH_RETRACT:
            if self._blocking:
                cmds.append(_cmd(CommandAction.KEY_UP, Key.shift, event))
                self._blocking = False

        return cmds

    def get_status(self) -> dict:
        return {
            "hero":       self.name,
            "form":       self._form.name,
            "blocking":   self._blocking,
            "last_event": self._last_event_name,
        }
