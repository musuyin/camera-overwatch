from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
import time

from pynput import keyboard as kb_mod, mouse as ms_mod
from gesture_recognizer import GestureEvent


class CommandAction(Enum):
    KEY_DOWN   = auto()
    KEY_UP     = auto()
    MOUSE_DOWN = auto()
    MOUSE_UP   = auto()


@dataclass
class GameCommand:
    action: CommandAction
    key: str | ms_mod.Button   # 字符串键名 或 pynput 鼠标按钮
    source_event: GestureEvent


class InputController:
    """封装 pynput，执行 GameCommand 并返回执行完成时间戳（ms）。"""

    def __init__(self):
        self._kb  = kb_mod.Controller()
        self._ms  = ms_mod.Controller()

    def execute(self, cmd: GameCommand) -> float:
        action = cmd.action
        key    = cmd.key

        if action == CommandAction.KEY_DOWN:
            self._kb.press(key)
        elif action == CommandAction.KEY_UP:
            self._kb.release(key)
        elif action == CommandAction.MOUSE_DOWN:
            self._ms.press(key)
        elif action == CommandAction.MOUSE_UP:
            self._ms.release(key)

        ts = time.monotonic() * 1000
        return ts
