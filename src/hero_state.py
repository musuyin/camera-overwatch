from __future__ import annotations
from abc import ABC, abstractmethod

from gesture_recognizer import GestureEvent


class HeroMapper(ABC):
    """所有英雄映射器的抽象基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """英雄名称，用于 HUD 显示。"""

    @abstractmethod
    def handle(self, event: GestureEvent) -> list:
        """
        接收一个 GestureEvent，返回需要执行的 GameCommand 列表。
        返回类型为 list[GameCommand]（避免循环导入）。
        """

    @abstractmethod
    def get_status(self) -> dict:
        """返回当前状态字典，用于 HUD 显示。"""
