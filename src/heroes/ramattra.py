from __future__ import annotations
from enum import Enum, auto
import logging
import time
from pynput.mouse import Button

from gesture.body_action import BodyAction
from heroes.base import HeroMapper, make_cmd
from input.controller import CommandAction, GameCommand

logger = logging.getLogger('gesture_overwatch')

NEMESIS_DURATION = 8.0  # 天罚形态持续时间（秒）


class FormState(Enum):
    OMNIC   = auto()
    NEMESIS = auto()


class RamattraMapper(HeroMapper):
    """
    拉玛莎（Ramattra）：位置区域 + 形态切换状态机型。

    普通形态（OMNIC）：
      右手伸出      → 左键持续按住（普攻）；收回释放
      右手抬至上区  → 右键单击
      左手伸出      → E 单击
      双手交叉      → 变身天罚形态（Q，8 秒自动退出）

    天罚形态（NEMESIS）：
      右手/左手伸出 → 左键单击（出拳）
      双手交叉      → 持续按住右键；再次交叉释放
      8 秒后        → 自动释放右键，退出天罚形态，打印日志
    """

    @property
    def name(self) -> str:
        return "Ramattra"

    def __init__(self):
        self._form             = FormState.OMNIC
        self._right_pressing   = False   # OMNIC 普攻左键是否按住
        self._nemesis_holding  = False   # NEMESIS 双手交叉右键是否按住
        self._nemesis_enter_ts = 0.0     # 进入天罚形态的时间戳（monotonic 秒）
        self._last_action_name = "-"

    def handle(self, action: BodyAction, timestamp: float) -> list[GameCommand]:
        self._last_action_name = action.name
        table = self._OMNIC_BINDINGS if self._form == FormState.OMNIC else self._NEMESIS_BINDINGS
        handler = table.get(action)
        return handler(self, timestamp) if handler else []

    def tick(self, timestamp: float) -> list[GameCommand]:
        """每帧调用：检查天罚形态是否到期。"""
        if self._form != FormState.NEMESIS:
            return []
        elapsed = time.monotonic() - self._nemesis_enter_ts
        if elapsed >= NEMESIS_DURATION:
            return self._nemesis_timeout(timestamp)
        return []

    # ------------------------------------------------------------------
    # OMNIC 形态
    # ------------------------------------------------------------------

    def _omnic_attack_down(self, ts: float) -> list[GameCommand]:
        if self._right_pressing:
            return []
        self._right_pressing = True
        return [make_cmd(CommandAction.MOUSE_DOWN, Button.left, ts)]

    def _omnic_attack_up(self, ts: float) -> list[GameCommand]:
        if not self._right_pressing:
            return []
        self._right_pressing = False
        return [make_cmd(CommandAction.MOUSE_UP, Button.left, ts)]

    def _omnic_right_click(self, ts: float) -> list[GameCommand]:
        return [
            make_cmd(CommandAction.MOUSE_DOWN, Button.right, ts),
            make_cmd(CommandAction.MOUSE_UP,   Button.right, ts),
        ]

    def _omnic_ability(self, ts: float) -> list[GameCommand]:
        return [make_cmd(CommandAction.KEY_DOWN, 'e', ts), make_cmd(CommandAction.KEY_UP, 'e', ts)]

    def _omnic_transform(self, ts: float) -> list[GameCommand]:
        cmds = self._omnic_attack_up(ts)   # 确保普攻松开
        self._form = FormState.NEMESIS
        self._nemesis_enter_ts = time.monotonic()
        logger.info("Ramattra → NEMESIS (%.0fs 后自动退出)", NEMESIS_DURATION)
        cmds += [make_cmd(CommandAction.KEY_DOWN, 'q', ts), make_cmd(CommandAction.KEY_UP, 'q', ts)]
        return cmds

    # ------------------------------------------------------------------
    # NEMESIS 形态
    # ------------------------------------------------------------------

    def _nemesis_punch(self, ts: float) -> list[GameCommand]:
        return [
            make_cmd(CommandAction.MOUSE_DOWN, Button.left, ts),
            make_cmd(CommandAction.MOUSE_UP,   Button.left, ts),
        ]

    def _nemesis_cross(self, ts: float) -> list[GameCommand]:
        if not self._nemesis_holding:
            self._nemesis_holding = True
            return [make_cmd(CommandAction.MOUSE_DOWN, Button.right, ts)]
        else:
            self._nemesis_holding = False
            return [make_cmd(CommandAction.MOUSE_UP, Button.right, ts)]

    def _nemesis_timeout(self, ts: float) -> list[GameCommand]:
        elapsed = time.monotonic() - self._nemesis_enter_ts
        logger.info("Ramattra NEMESIS 到期 (%.1fs)，退出天罚形态", elapsed)
        cmds = []
        if self._nemesis_holding:
            self._nemesis_holding = False
            cmds.append(make_cmd(CommandAction.MOUSE_UP, Button.right, ts))
        self._form = FormState.OMNIC
        return cmds

    # ------------------------------------------------------------------
    # 绑定表
    # ------------------------------------------------------------------

    _OMNIC_BINDINGS: dict = {
        BodyAction.RIGHT_EXTEND:   _omnic_attack_down,
        BodyAction.RIGHT_RETRACT:  _omnic_attack_up,
        BodyAction.RIGHT_ZONE_TOP: _omnic_right_click,
        BodyAction.LEFT_EXTEND:    _omnic_ability,
        BodyAction.BOTH_CROSS:     _omnic_transform,
    }

    _NEMESIS_BINDINGS: dict = {
        BodyAction.RIGHT_EXTEND: _nemesis_punch,
        BodyAction.LEFT_EXTEND:  _nemesis_punch,
        BodyAction.BOTH_CROSS:   _nemesis_cross,
    }

    def get_status(self) -> dict:
        remaining = 0.0
        if self._form == FormState.NEMESIS:
            remaining = max(0.0, NEMESIS_DURATION - (time.monotonic() - self._nemesis_enter_ts))
        return {
            "hero":        self.name,
            "form":        self._form.name,
            "holding":     self._nemesis_holding,
            "nemesis_rem": f"{remaining:.1f}s" if self._form == FormState.NEMESIS else "-",
            "last_action": self._last_action_name,
        }
