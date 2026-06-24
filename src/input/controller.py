from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
import platform
import time

from pynput import keyboard as kb_mod, mouse as ms_mod
from pynput.keyboard import Key
from pynput.mouse import Button

_IS_WINDOWS = platform.system() == "Windows"

if _IS_WINDOWS:
    import pydirectinput
    pydirectinput.PAUSE = 0

_KEY_NAME: dict = {
    Key.shift:  'shift',
    Key.ctrl:   'ctrl',
    Key.alt:    'alt',
    Key.enter:  'enter',
    Key.space:  'space',
    Key.tab:    'tab',
    Key.esc:    'esc',
}
_BTN_NAME: dict = {
    Button.left:   'left',
    Button.right:  'right',
    Button.middle: 'middle',
}


class CommandAction(Enum):
    KEY_DOWN   = auto()
    KEY_UP     = auto()
    MOUSE_DOWN = auto()
    MOUSE_UP   = auto()


@dataclass
class GameCommand:
    action:    CommandAction
    key:       str | Button
    timestamp: float          # 来源手势事件的时间戳（ms），用于延迟测量


class InputController:
    """
    键鼠输出封装。
    - Windows：使用 pydirectinput（扫描码），可穿透游戏输入隔离
    - macOS：使用 pynput
    """

    def __init__(self):
        if not _IS_WINDOWS:
            self._kb = kb_mod.Controller()
            self._ms = ms_mod.Controller()

    def execute(self, cmd: GameCommand) -> float:
        if _IS_WINDOWS:
            self._execute_directinput(cmd)
        else:
            self._execute_pynput(cmd)
        return time.monotonic() * 1000

    def _execute_directinput(self, cmd: GameCommand) -> None:
        action = cmd.action
        key    = cmd.key

        if action in (CommandAction.KEY_DOWN, CommandAction.KEY_UP):
            name = _KEY_NAME.get(key, key)
            if action == CommandAction.KEY_DOWN:
                pydirectinput.keyDown(name)
            else:
                pydirectinput.keyUp(name)
        elif action in (CommandAction.MOUSE_DOWN, CommandAction.MOUSE_UP):
            btn = _BTN_NAME.get(key, 'left')
            if action == CommandAction.MOUSE_DOWN:
                pydirectinput.mouseDown(button=btn)
            else:
                pydirectinput.mouseUp(button=btn)

    def _execute_pynput(self, cmd: GameCommand) -> None:
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
