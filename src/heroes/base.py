from __future__ import annotations
from abc import ABC, abstractmethod

from gesture.body_action import BodyAction


class HeroMapper(ABC):
    """所有英雄映射器的抽象基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """英雄名称，用于 HUD 显示。"""

    @abstractmethod
    def handle(self, action: BodyAction, timestamp: float) -> list:
        """接收一个 BodyAction 和事件时间戳，返回 GameCommand 列表。"""

    @abstractmethod
    def get_status(self) -> dict:
        """返回当前状态字典，用于 HUD 显示。"""
