from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
import platform
import time

from pynput import keyboard as kb_mod, mouse as ms_mod
from pynput.keyboard import Key
from pynput.mouse import Button

_IS_WINDOWS = platform.system() == "Windows"

# Windows 后端：优先 Interception 内核驱动，降级到 pydirectinput
_interception  = None
_pydirectinput = None

if _IS_WINDOWS:
    try:
        import interception as _interception
    except Exception:
        _interception = None
    if _interception is None:
        try:
            import pydirectinput as _pydirectinput
            _pydirectinput.PAUSE = 0
        except Exception:
            _pydirectinput = None

# ── 键盘扫描码表（Interception 使用硬件扫描码）────────────────────────────────
# 字符串键名 → 扫描码（只列出项目实际用到的键，按需扩充）
_SCAN_CODE: dict = {
    'q': 0x10, 'e': 0x12,
    'shift': 0x2A,   # Left Shift
    'ctrl':  0x1D,   # Left Ctrl
    'alt':   0x38,   # Left Alt
    'enter': 0x1C,
    'space': 0x39,
    'tab':   0x0F,
    'esc':   0x01,
}
# pynput Key 对象直接映射到同一张扫描码表（避免两份重复定义）
_KEY_SCAN: dict = {
    Key.shift: _SCAN_CODE['shift'],
    Key.ctrl:  _SCAN_CODE['ctrl'],
    Key.alt:   _SCAN_CODE['alt'],
    Key.enter: _SCAN_CODE['enter'],
    Key.space: _SCAN_CODE['space'],
    Key.tab:   _SCAN_CODE['tab'],
    Key.esc:   _SCAN_CODE['esc'],
}

# Interception 鼠标状态常量（取自 C 头文件标准值，用 getattr 兼容不同绑定版本）
def _ic_const(name: str, default: int) -> int:
    return getattr(_interception, name, default) if _interception else default

_KEY_DOWN_STATE = _ic_const('INTERCEPTION_KEY_DOWN', 0x00)
_KEY_UP_STATE   = _ic_const('INTERCEPTION_KEY_UP',   0x01)
_BTN_STATES: dict = {
    'left':   (_ic_const('INTERCEPTION_MOUSE_LEFT_BUTTON_DOWN',   0x0001),
               _ic_const('INTERCEPTION_MOUSE_LEFT_BUTTON_UP',     0x0002)),
    'right':  (_ic_const('INTERCEPTION_MOUSE_RIGHT_BUTTON_DOWN',  0x0004),
               _ic_const('INTERCEPTION_MOUSE_RIGHT_BUTTON_UP',    0x0008)),
    'middle': (_ic_const('INTERCEPTION_MOUSE_MIDDLE_BUTTON_DOWN', 0x0010),
               _ic_const('INTERCEPTION_MOUSE_MIDDLE_BUTTON_UP',   0x0020)),
}

# Interception 设备号约定：1-10 为键盘，11-20 为鼠标
_KBD_DEVICE   = 1
_MOUSE_DEVICE = 11

# pynput Key/Button → pydirectinput 字符串（降级用）
_PYDIRECT_KEY: dict = {
    Key.shift: 'shift', Key.ctrl: 'ctrl', Key.alt: 'alt',
    Key.enter: 'enter', Key.space: 'space', Key.tab: 'tab', Key.esc: 'esc',
}
_PYDIRECT_BTN: dict = {
    Button.left: 'left', Button.right: 'right', Button.middle: 'middle',
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
    键鼠输出封装，三层策略：
    1. Windows + Interception 驱动  →  内核级扫描码注入，穿透反外挂
    2. Windows，无驱动              →  pydirectinput（SendInput 扫描码）
    3. macOS                        →  pynput
    """

    def __init__(self):
        if _IS_WINDOWS:
            if _interception is not None:
                # 只创建上下文，不调用 auto_capture_devices
                # auto_capture_devices(keyboard=True) 会拦截真实键盘输入导致键盘失效
                self._ctx = _interception.interception()
                print("[InputController] 使用 Interception 内核驱动")
            elif _pydirectinput is not None:
                print(
                    "[InputController] 未检测到 Interception 驱动，降级为 pydirectinput\n"
                    "  游戏内可能无法接收输入，建议安装驱动：\n"
                    "  https://github.com/oblitum/Interception/releases"
                )
            else:
                print("[InputController] 警告：Windows 下无可用输入后端")
        else:
            self._kb = kb_mod.Controller()
            self._ms = ms_mod.Controller()

    def execute(self, cmd: GameCommand) -> float:
        if _IS_WINDOWS:
            if _interception is not None:
                self._execute_interception(cmd)
            elif _pydirectinput is not None:
                self._execute_directinput(cmd)
        else:
            self._execute_pynput(cmd)
        return time.monotonic() * 1000

    # ------------------------------------------------------------------
    # Interception（内核级，不拦截真实输入）
    # ------------------------------------------------------------------

    def _execute_interception(self, cmd: GameCommand) -> None:
        action = cmd.action
        key    = cmd.key

        if action in (CommandAction.KEY_DOWN, CommandAction.KEY_UP):
            scan = _KEY_SCAN.get(key) if isinstance(key, Key) else _SCAN_CODE.get(str(key).lower())
            if scan is None:
                return
            state  = _KEY_DOWN_STATE if action == CommandAction.KEY_DOWN else _KEY_UP_STATE
            stroke = _interception.key_stroke(scan, state, 0)
            self._ctx.send(_KBD_DEVICE, stroke)

        elif action in (CommandAction.MOUSE_DOWN, CommandAction.MOUSE_UP):
            btn       = _PYDIRECT_BTN.get(key, 'left')
            down_f, up_f = _BTN_STATES[btn]
            flags     = down_f if action == CommandAction.MOUSE_DOWN else up_f
            stroke    = _interception.mouse_stroke(flags, 0, 0, 0)
            self._ctx.send(_MOUSE_DEVICE, stroke)

    # ------------------------------------------------------------------
    # pydirectinput（SendInput 扫描码，降级）
    # ------------------------------------------------------------------

    def _execute_directinput(self, cmd: GameCommand) -> None:
        action = cmd.action
        key    = cmd.key

        if action in (CommandAction.KEY_DOWN, CommandAction.KEY_UP):
            name = _PYDIRECT_KEY.get(key, key)
            if action == CommandAction.KEY_DOWN:
                _pydirectinput.keyDown(name)
            else:
                _pydirectinput.keyUp(name)
        elif action in (CommandAction.MOUSE_DOWN, CommandAction.MOUSE_UP):
            btn = _PYDIRECT_BTN.get(key, 'left')
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
