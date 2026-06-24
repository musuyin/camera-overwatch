"""
输入模拟验证脚本。

运行后有 3 秒切换窗口到文本编辑器（TextEdit / 记事本），
然后依次触发键盘和鼠标事件，观察是否在编辑器中生效。

用法：
    python test_input.py
"""
import time
import sys
from pynput.keyboard import Controller as KbCtrl, Key
from pynput.mouse    import Controller as MsCtrl, Button

DELAY = 3  # 切换窗口的准备时间（秒）

kb = KbCtrl()
ms = MsCtrl()


def countdown(n: int) -> None:
    for i in range(n, 0, -1):
        print(f"  {i}...", end="\r", flush=True)
        time.sleep(1)
    print()


def test_keyboard() -> None:
    print("\n[1/3] 键盘测试：将输入 hello<Enter>")
    countdown(DELAY)
    for ch in "hello":
        kb.press(ch)
        kb.release(ch)
        time.sleep(0.05)
    kb.press(Key.enter)
    kb.release(Key.enter)
    print("  键盘输入完成，检查编辑器中是否出现 'hello'")


def test_special_keys() -> None:
    print("\n[2/3] 特殊键测试：Shift + q（应输入大写 Q）")
    countdown(DELAY)
    with kb.pressed(Key.shift):
        kb.press('q')
        kb.release('q')
    kb.press(Key.enter)
    kb.release(Key.enter)
    print("  完成，检查是否出现 'Q'")


def test_mouse() -> None:
    print("\n[3/3] 鼠标测试：左键单击（当前鼠标位置）")
    print(f"  当前鼠标坐标：{ms.position}")
    countdown(DELAY)
    ms.press(Button.left)
    time.sleep(0.05)
    ms.release(Button.left)
    print("  鼠标点击完成")


if __name__ == "__main__":
    print("=== pynput 输入模拟验证 ===")
    print(f"请在 {DELAY} 秒内切换到文本编辑器（TextEdit / 记事本）并点击输入区域\n")

    try:
        test_keyboard()
        test_special_keys()
        test_mouse()
    except Exception as e:
        print(f"\n错误：{e}", file=sys.stderr)
        print("macOS：请确认 Terminal 已获得「辅助功能」权限", file=sys.stderr)
        print("Windows：以普通权限运行即可（无需管理员）", file=sys.stderr)
        sys.exit(1)

    print("\n=== 测试完成 ===")
