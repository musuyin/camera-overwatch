from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
import platform
import time

from pynput import keyboard as kb_mod, mouse as ms_mod
from pynput.keyboard import Key
from pynput.mouse import Button

_IS_WINDOWS = platform.system() == "Windows"

# Windows 后端：优先 interception（内核驱动，可穿透反外挂），降级到 pydirectinput
_interception = None
if _IS_WINDOWS:
    try:
        import interception as _interception
    except Exception:
        _interception = None
    if _interception is None:
        import pydirectinput as _pydirectinput
        _pydirectinput.PAUSE = 0
    else:
        _pydirectinput = None

# pynput Key/Button → interception/pydirectinput 字符串
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

# interception 鼠标按钮常量（仅 Windows + 驱动已安装时有效）
_INTERCEPTION_BTN: dict = {}
if _IS_WINDOWS and _interception is not None:
    _INTERCEPTION_BTN = {
        'left':   (_interception.INTERCEPTION_MOUSE_LEFT_BUTTON_DOWN,
                   _interception.INTERCEPTION_MOUSE_LEFT_BUTTON_UP),
        'right':  (_interception.INTERCEPTION_MOUSE_RIGHT_BUTTON_DOWN,
                   _interception.INTERCEPTION_MOUSE_RIGHT_BUTTON_UP),
        'middle': (_interception.INTERCEPTION_MOUSE_MIDDLE_BUTTON_DOWN,
                   _interception.INTERCEPTION_MOUSE_MIDDLE_BUTTON_UP),
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
    键鼠输出封装，三层降级策略：
    1. Windows + Interception 驱动 → 内核级注入，游戏无法过滤
    2. Windows，无驱动             → pydirectinput（扫描码 SendInput）
    3. macOS                       → pynput
    """

    def __init__(self):
        if _IS_WINDOWS:
            if _interception is not None:
                self._ctx = _interception.interception()
                self._ctx.auto_capture_devices(keyboard=True, mouse=True)
            else:
                print(
                    "[InputController] 未检测到 Interception 驱动，使用 pydirectinput 降级模式。\n"
                    "  游戏内可能无法接收输入，建议安装驱动：\n"
                    "  https://github.com/oblitum/Interception/releases"
                )
        else:
            self._kb = kb_mod.Controller()
            self._ms = ms_mod.Controller()

    def execute(self, cmd: GameCommand) -> float:
        if _IS_WINDOWS:
            if _interception is not None:
                self._execute_interception(cmd)
            else:
                self._execute_directinput(cmd)
        else:
            self._execute_pynput(cmd)
        return time.monotonic() * 1000

    # ------------------------------------------------------------------
    # Interception（内核驱动）
    # ------------------------------------------------------------------

    def _execute_interception(self, cmd: GameCommand) -> None:
        action = cmd.action
        key    = cmd.key

        if action in (CommandAction.KEY_DOWN, CommandAction.KEY_UP):
            name    = _KEY_NAME.get(key, key)
            stroke  = _interception.key_stroke(
                _interception.str_to_key(name.upper()),
                _interception.INTERCEPTION_KEY_DOWN if action == CommandAction.KEY_DOWN
                else _interception.INTERCEPTION_KEY_UP,
            )
            self._ctx.send_to_keyboard(stroke)

        elif action in (CommandAction.MOUSE_DOWN, CommandAction.MOUSE_UP):
            btn      = _BTN_NAME.get(key, 'left')
            down_f, up_f = _INTERCEPTION_BTN[btn]
            flags    = down_f if action == CommandAction.MOUSE_DOWN else up_f
            stroke   = _interception.mouse_stroke(flags, 0, 0)
            self._ctx.send_to_mouse(stroke)

    # ------------------------------------------------------------------
    # pydirectinput（扫描码 SendInput，无驱动降级）
    # ------------------------------------------------------------------

    def _execute_directinput(self, cmd: GameCommand) -> None:
        action = cmd.action
        key    = cmd.key

        if action in (CommandAction.KEY_DOWN, CommandAction.KEY_UP):
            name = _KEY_NAME.get(key, key)
            if action == CommandAction.KEY_DOWN:
                _pydirectinput.keyDown(name)
            else:
                _pydirectinput.keyUp(name)
        elif action in (CommandAction.MOUSE_DOWN, CommandAction.MOUSE_UP):
            btn = _BTN_NAME.get(key, 'left')
            if action == CommandAction.MOUSE_DOWN:
                _pydirectinput.mouseDown(button=btn)
            else:
                _pydirectinput.mouseUp(button=btn)

    # ------------------------------------------------------------------
    # pynput（macOS）
    # ------------------------------------------------------------------

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
