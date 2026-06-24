# Gesture Overwatch

基于手势识别的守望先锋体感控制系统。通过摄像头捕捉手势，映射为键鼠输入，操控游戏英雄。

## 功能

- 实时双手关键点检测（MediaPipe，21点，CPU 可达 30fps）
- 手势识别：伸缩、位置区域（上/中/下）、双手交叉、甩手
- 支持两个英雄，各有独立手势映射逻辑
- 实时 HUD：当前英雄、手势状态、触发指令、延迟、FPS
- 去抖处理（~133ms），过滤手抖和过渡姿态

## 环境要求

- Python 3.10+
- 摄像头（默认 ID=0）
- Windows 运行时：pynput 无需额外配置
- macOS 运行时：需在「系统偏好设置 → 隐私与安全性 → 辅助功能」中授权 Terminal

## 安装

根据操作系统选择对应的依赖文件（`pyobjc-*` 是 pynput 在 macOS 上的后端，Windows 不需要）：

```bash
# macOS
pip install -r requirements-mac.txt

# Windows
pip install -r requirements-windows.txt
```

然后下载模型文件（仅需一次）：

```bash
python scripts/setup_model.py
```

### Windows 游戏内输入（Interception 驱动）

程序在 Windows 上默认使用 **Interception 内核驱动**注入输入，可穿透 Overwatch 的 `LLMHF_INJECTED` 过滤。安装步骤：

1. 从 [Interception Releases](https://github.com/oblitum/Interception/releases) 下载安装包
2. **以管理员身份**运行安装程序
3. **重启电脑**（驱动必须在系统启动时加载）

未安装驱动时程序自动降级为 `pydirectinput`，游戏外测试可用，但游戏内可能无效。

## 运行

```bash
cd src
python main.py
```

启动后选择英雄（1 或 2），摄像头窗口打开后按 **ESC** 退出。

> 网络受限时可手动下载模型文件后放入 `src/` 目录：
> `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`

## 英雄手势映射

### 莫伊拉（Moira）

| 用户动作 | 识别维度 | 游戏指令 |
|----------|----------|----------|
| 左手向前伸出 | 左手伸出 | 鼠标左键按住（治疗光束） |
| 左手收回 | 左手收回 | 鼠标左键释放 |
| 左手上抬 | 左手区域：上 | E + 左键（扔治疗球） |
| 右手向前伸出 | 右手伸出 | 鼠标右键按住（伤害光束） |
| 右手收回 | 右手收回 | 鼠标右键释放 |
| 右手上抬 | 右手区域：上 | E + 右键（扔伤害球） |
| 双手同时向前伸出 | 双手同时伸出 | Q（大招） |

### 拉玛莎（Ramattra）

**普通形态（OMNIC）**

| 用户动作 | 识别维度 | 游戏指令 |
|----------|----------|----------|
| 右手向前伸出 | 右手伸出 | 鼠标左键按住（普攻） |
| 右手收回 | 右手收回 | 鼠标左键释放 |
| 右手上抬 | 右手区域：上 | 鼠标右键单击 |
| 左手向前伸出 | 左手伸出 | E 单击 |
| 双手手腕交叉 | 双手交叉 | Q（变身天罚形态） |

**天罚形态（NEMESIS）**

| 用户动作 | 识别维度 | 游戏指令 |
|----------|----------|----------|
| 右手向前伸出 | 右手伸出 | 鼠标左键单击（右拳） |
| 左手向前伸出 | 左手伸出 | 鼠标左键单击（左拳） |
| 双手手腕交叉（第一次） | 双手交叉 | 鼠标右键按住（格挡） |
| 双手手腕交叉（第二次） | 双手交叉 | 鼠标右键释放 + 退出天罚形态 |

## 配置参数

配置文件：[src/config.py](src/config.py)

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CAMERA_ID` | `0` | 摄像头设备 ID |
| `TARGET_FPS` | `30` | 目标帧率 |
| `DEBOUNCE_FRAMES` | `4` | 去抖帧数（~133ms @ 30fps） |
| `EXTEND_THRESHOLD` | `8000` | 手掌面积阈值（像素²），需按摄像头分辨率标定 |
| `ZONE_TOP_BOUNDARY` | `0.35` | 上区域边界（归一化 y，小于此值为 TOP） |
| `ZONE_BOTTOM_BOUNDARY` | `0.65` | 下区域边界（归一化 y，大于此值为 BOTTOM） |
| `SWIPE_MIN_VELOCITY` | `0.03` | 甩手触发最小速度（归一化坐标/帧） |
| `SWIPE_FRAMES` | `5` | 甩手速度计算滑动窗口帧数 |
| `DEBUG_LOG` | `False` | 开启后在控制台打印每帧指令和延迟 |

> **首次使用需标定 `EXTEND_THRESHOLD`**：开启 `DEBUG_LOG = True`，伸出和收回手掌，观察控制台中 `palm_area` 的值范围，将中间值填入该参数。

## 目录结构

```
src/
├── main.py                     入口，英雄选择 + 主循环 + HUD 渲染
├── config.py                   全局参数
├── vision/                     采集层 + 追踪层
│   ├── capture.py              摄像头采集
│   └── hand_tracker.py         MediaPipe 封装，输出双手关键点
├── gesture/                    识别层
│   ├── recognizer.py           手势识别规则引擎（伸缩/区域/交叉/甩手/去抖）
│   └── body_action.py          BodyAction 枚举 + GestureType → BodyAction 映射表
├── heroes/                     映射层
│   ├── base.py                 HeroMapper 抽象基类
│   ├── moira.py                莫伊拉映射逻辑
│   └── ramattra.py             拉玛莎状态机映射逻辑
└── input/                      输出层
    └── controller.py           键鼠输出封装（Windows: pydirectinput，macOS: pynput）
```

## HUD 说明

程序运行时摄像头窗口左上角显示：

```
Hero: Moira
Left:  EXTENDING  
Right: retracted
Last:  LEFT_EXTEND
Latency: 42.3ms
FPS: 28.5
```

- **Left / Right**：当前手的状态
- **Last**：最近触发的手势事件名
- **Latency**：从手势识别到指令注入的端到端延迟
