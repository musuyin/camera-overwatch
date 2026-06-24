# CLAUDE.md

## 项目概述

基于手势识别的守望先锋体感控制系统。通过 MediaPipe 实时识别双手关键点，将手势映射为 pynput 键鼠输入。源码在 `src/` 目录下。

## 代码修改后必须同步 README.md

**每次修改代码后，必须同步更新 `README.md`，确保以下内容与代码保持一致：**

- 目录结构（新增/删除/重命名文件时）
- 配置参数表（`config.py` 中的参数变更时）
- 手势映射表（英雄手势逻辑变更时）
- 依赖列表（新增/移除依赖时）
- 运行说明（入口、参数、用法变更时）

## 目录结构

```
src/
├── main.py                     入口，英雄选择 + 主循环 + HUD 渲染
├── config.py                   全局参数（阈值、摄像头ID、区域边界）
├── vision/                     采集层 + 追踪层
│   ├── capture.py              摄像头采集（CaptureModule）
│   └── hand_tracker.py         MediaPipe 封装（HandTracker + HandData）
├── gesture/                    识别层
│   ├── recognizer.py           手势识别规则引擎（GestureRecognizer + GestureEvent）
│   └── body_action.py          BodyAction 枚举 + GESTURE_TO_ACTION 映射表
├── heroes/                     映射层
│   ├── base.py                 HeroMapper 抽象基类
│   ├── moira.py                莫伊拉：双手独立状态映射
│   └── ramattra.py             拉玛莎：OMNIC/NEMESIS 状态机
└── input/                      输出层
    └── controller.py           pynput/pydirectinput 封装（InputController + GameCommand）
```

## 架构分层

```
采集层（capture.py）→ 追踪层（hand_tracker.py）→ 识别层（gesture_recognizer.py）
→ 映射层（heroes/）→ 输出层（input_mapper.py）
```

各层间通过 dataclass 传递数据，不直接持有上下游引用。

## 关键约定

- **特殊键必须用 `pynput.keyboard.Key`**，不能用字符串。例如 `Key.shift`，不能写 `'shift'`。单字符键（`'e'`、`'q'`）可以直接用字符串。
- `GestureRecognizer` 是唯一维护帧间历史状态的模块（除 `HeroMapper` 的业务状态机）。
- 去抖阈值：状态连续保持 `DEBOUNCE_FRAMES` 帧后才触发事件，甩手检测不走去抖。
- 摄像头帧在主循环中水平翻转（`cv2.flip`），交叉判断逻辑基于翻转后坐标。
- `EXTEND_THRESHOLD` 单位为像素²，首次使用需按摄像头分辨率标定。

## 开发环境

- Python 3.12（venv 在 `venv/`）
- 开发平台：macOS，目标运行平台：Windows
- 依赖：`mediapipe opencv-python pynput numpy`
