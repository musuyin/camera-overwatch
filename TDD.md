# 技术设计文档：基于手势识别的守望先锋体感控制系统

**版本**：v1.0  
**日期**：2026-06-14  
**作者**：木素音  
**依赖文档**：PRD v1.1

---

## 一、技术选型

| 技术 | 版本 | 用途 | 选型理由 |
|------|------|------|----------|
| Python | 3.10+ | 主语言 | MediaPipe、OpenCV、pynput 均有完善 Python 支持，生态一致 |
| OpenCV (`cv2`) | 4.x | 摄像头采集、画面渲染 | 跨平台视觉处理标准库，帧处理 API 成熟稳定 |
| MediaPipe Hands | 0.10.x | 手部关键点检测 | Google 出品，21点手部模型，免训练，实时性好（CPU 可达 30fps） |
| pynput | 1.7.x | 键鼠事件模拟 | 支持按键持续按住/释放语义，适合游戏连续输入场景，优于 pyautogui |
| numpy | 1.x | 关键点坐标计算 | 向量运算、面积估算、帧间差分的基础依赖 |

---

## 二、整体架构设计

### 分层架构

系统为单体应用，采用**管线分层架构**，数据单向流动，各层职责隔离：

```
┌─────────────────────────────────────────┐
│           采集层（Capture Layer）         │  摄像头读帧，输出 BGR 原始帧
├─────────────────────────────────────────┤
│           追踪层（Tracking Layer）        │  MediaPipe 推理，输出双手关键点
├─────────────────────────────────────────┤
│           识别层（Recognition Layer）     │  几何规则引擎，输出离散手势事件
├─────────────────────────────────────────┤
│           映射层（Mapping Layer）         │  英雄状态机，手势事件 → 游戏指令
├─────────────────────────────────────────┤
│           输出层（Output Layer）          │  pynput 模拟键鼠输入
└─────────────────────────────────────────┘
         ↕ 每层向上返回结果，向下不依赖
```

### 模块划分与交互关系

```
main.py
  │
  ├── CaptureModule          从摄像头逐帧读取，转换色彩空间
  │       │
  ├── HandTracker            封装 MediaPipe，接收帧，返回 HandData 列表
  │       │
  ├── GestureRecognizer      接收 HandData，维护帧间状态，输出 GestureEvent 列表
  │       │
  ├── HeroMapper（抽象基类）
  │   ├── MoiraMapper        订阅 GestureEvent，维护左右手独立状态，触发指令
  │   └── RamattraMapper     订阅 GestureEvent，维护 FormState 状态机，触发指令
  │       │
  ├── InputController        接收指令，调用 pynput 执行键鼠事件
  │       │
  └── HUDRenderer            接收帧、HandData、当前状态，叠加调试信息后显示
```

**关键交互约定**：
- 每一帧驱动一次完整管线，主循环在 `main.py` 中串行执行
- 各模块间通过**数据类（dataclass）传递**，不直接持有上下游模块引用
- `GestureRecognizer` 是唯一维护帧间历史状态的模块，其他模块无状态（除 `HeroMapper` 的业务状态机）

---

## 三、核心数据类设计

### 3.1 HandData（追踪层输出）

```
HandData
  ├── handedness: str          # "Left" 或 "Right"，MediaPipe 标注
  ├── landmarks: list[Point3D] # 21个关键点，归一化坐标（x∈[0,1], y∈[0,1], z相对深度）
  ├── wrist: Point3D           # landmarks[0] 的快捷引用
  └── palm_area: float         # 手掌面积估算值（像素平方，反映伸缩程度）

Point3D
  ├── x: float
  ├── y: float
  └── z: float
```

### 3.2 HandState（识别层内部，帧间维护）

```
HandState
  ├── handedness: str
  ├── position_zone: PositionZone   # 枚举：TOP / MID / BOTTOM
  ├── extension: Extension          # 枚举：EXTENDED / RETRACTED
  ├── velocity: Vector2D            # 当前帧与前N帧手腕位移均值
  └── stable_frames: int            # 当前状态已连续保持的帧数（用于去抖）

PositionZone  枚举值：TOP | MID | BOTTOM
Extension     枚举值：EXTENDED | RETRACTED
```

### 3.3 GestureEvent（识别层输出）

```
GestureEvent
  ├── hand: str                  # "Left" 或 "Right" 或 "Both"
  ├── gesture_type: GestureType  # 枚举，见下方
  └── timestamp: float           # 触发时间戳（ms），用于延迟测量

GestureType  枚举值：
  LEFT_EXTEND | LEFT_RETRACT
  RIGHT_EXTEND | RIGHT_RETRACT
  LEFT_ZONE_TOP | LEFT_ZONE_MID | LEFT_ZONE_BOTTOM
  RIGHT_ZONE_TOP | RIGHT_ZONE_MID | RIGHT_ZONE_BOTTOM
  BOTH_EXTEND | BOTH_CROSS
  SWIPE_LEFT | SWIPE_RIGHT       # 横向甩手（莫伊拉扔球用）
```

### 3.4 GameCommand（映射层输出）

```
GameCommand
  ├── action: CommandAction   # 枚举：KEY_DOWN / KEY_UP / MOUSE_DOWN / MOUSE_UP
  ├── key: str | MouseButton  # 对应按键或鼠标键
  └── source_event: GestureEvent  # 来源事件，用于延迟追踪
```

### 3.5 FormState（拉玛莎状态机）

```
FormState  枚举值：OMNIC | NEMESIS
```

---

## 四、核心业务逻辑流程

### 4.1 主循环流程

```
初始化所有模块
选择英雄，实例化对应 HeroMapper

LOOP:
  读取摄像头帧
  若读取失败 → 跳过本帧

  调用 HandTracker，得到本帧 HandData 列表（0、1或2只手）
  调用 GestureRecognizer.update(hand_data_list)
    → 返回本帧触发的 GestureEvent 列表（可为空）

  对每个 GestureEvent:
    调用 HeroMapper.handle(event)
      → 返回 GameCommand 列表
    对每个 GameCommand:
      调用 InputController.execute(command)

  调用 HUDRenderer 叠加调试信息，显示帧

  若用户按 ESC → 退出循环

释放资源
```

### 4.2 手势识别去抖流程

目的：过滤手抖和过渡姿态，只有状态稳定保持 N 帧后才触发事件。

```
每帧 update(hand_data):
  计算当前帧的 extension、position_zone

  若与上一帧状态相同:
    stable_frames += 1
  否则:
    stable_frames = 1
    记录新候选状态

  若 stable_frames == DEBOUNCE_FRAMES（配置项，默认4帧≈133ms@30fps）:
    且候选状态与上次已触发状态不同:
      生成 GestureEvent 并加入输出队列
      更新上次已触发状态
```

### 4.3 伸缩判断流程

```
计算手掌面积：
  取 landmarks 中手掌四个角点（食指根、小指根、大拇指根、手腕）
  用叉积公式计算四边形面积

若面积 > EXTEND_THRESHOLD（配置项）:
  extension = EXTENDED
否则:
  extension = RETRACTED
```

> 选用面积而非 z 轴：z 轴为 MediaPipe 相对深度估算，精度低；手掌面积在 2D 图像中随前推后缩变化显著且稳定。

### 4.4 双手交叉判断流程

```
若本帧同时检测到左右手:
  left_wrist_x  = 左手 landmarks[0].x
  right_wrist_x = 右手 landmarks[0].x

  正常状态：left_wrist_x < right_wrist_x（左手在画面左侧）
  交叉状态：left_wrist_x > right_wrist_x（左手越过到右侧）

  对交叉状态同样经过去抖模块确认后，生成 BOTH_CROSS 事件
```

### 4.5 莫伊拉映射逻辑

```
维护状态：
  left_pressing: bool = False
  right_pressing: bool = False

收到 LEFT_EXTEND  → 若 !left_pressing:  发出 MOUSE_DOWN(左键),  left_pressing=True
收到 LEFT_RETRACT → 若 left_pressing:   发出 MOUSE_UP(左键),    left_pressing=False
收到 RIGHT_EXTEND → 若 !right_pressing: 发出 MOUSE_DOWN(右键),  right_pressing=True
收到 RIGHT_RETRACT→ 若 right_pressing:  发出 MOUSE_UP(右键),    right_pressing=False
收到 SWIPE_LEFT / SWIPE_RIGHT → 发出 KEY_DOWN(E) + KEY_UP(E)（单次触发）
收到 BOTH_EXTEND  → 发出 KEY_DOWN(Q) + KEY_UP(Q)
```

### 4.6 拉玛莎映射逻辑（状态机）

```
维护状态：form: FormState = OMNIC

收到 BOTH_CROSS:
  若 form == OMNIC  → form = NEMESIS，发出 KEY_DOWN(Q) + KEY_UP(Q)
  若 form == NEMESIS→ form = OMNIC（天罚形态自然结束，无需额外按键）

若 form == OMNIC:
  收到 RIGHT_EXTEND             → 发出 MOUSE_DOWN(左键) + MOUSE_UP(左键)（普攻点击）
  收到 RIGHT_ZONE_TOP（持续）   → 发出 KEY_DOWN(Shift)
  收到 RIGHT_ZONE_MID（离开TOP）→ 发出 KEY_UP(Shift)
  收到 RIGHT_ZONE_BOTTOM        → 发出 KEY_DOWN(E) + KEY_UP(E)

若 form == NEMESIS:
  收到 RIGHT_EXTEND → 发出 MOUSE_DOWN(左键) + MOUSE_UP(左键)（右拳）
  收到 LEFT_EXTEND  → 发出 MOUSE_DOWN(右键) + MOUSE_UP(右键)（左拳）
  收到 BOTH_EXTEND  → 发出 KEY_DOWN(Shift)（格挡持续）
  收到 BOTH_RETRACT → 发出 KEY_UP(Shift)（释放格挡）
```

---

## 五、关键依赖与外部服务

### 第三方库依赖

| 依赖 | 用途 | 模块 |
|------|------|------|
| `mediapipe` | 手部关键点推理 | HandTracker |
| `opencv-python` | 摄像头读帧、图像渲染 | CaptureModule、HUDRenderer |
| `pynput` | 键盘/鼠标事件注入 | InputController |
| `numpy` | 坐标计算、面积估算 | GestureRecognizer |

### 模块间依赖关系

```
main.py
  依赖 → CaptureModule、HandTracker、GestureRecognizer、HeroMapper、InputController、HUDRenderer

GestureRecognizer
  依赖 → HandData（来自 HandTracker 输出）
  依赖 → config.py（DEBOUNCE_FRAMES、EXTEND_THRESHOLD、ZONE_BOUNDARY 等阈值）

HeroMapper（MoiraMapper / RamattraMapper）
  依赖 → GestureEvent（来自 GestureRecognizer 输出）
  依赖 → InputController（发出 GameCommand）

HUDRenderer
  依赖 → HandData（绘制关键点）
  依赖 → HeroMapper.get_status()（获取当前状态用于显示）
```

### 外部系统依赖

| 外部系统 | 交互方式 | 说明 |
|----------|----------|------|
| 《守望先锋》游戏客户端 | pynput 系统级键鼠注入 | 游戏需在前台运行，使用训练模式/自定义对局避免反外挂 |
| 摄像头硬件 | OpenCV VideoCapture | 默认设备ID=0，可在 config.py 中修改 |

---

## 六、数据存储设计

本系统为**纯内存实时处理系统**，无持久化存储需求。

### 内存中的关键数据生命周期

| 数据 | 生命周期 | 存储位置 |
|------|----------|----------|
| 当前帧 BGR 图像 | 单帧，处理完即丢弃 | CaptureModule 局部变量 |
| HandData 列表 | 单帧，传递给下游后丢弃 | 主循环局部变量 |
| HandState（含帧历史） | 跨帧，常驻内存 | GestureRecognizer 实例变量 |
| FormState | 跨帧，常驻内存 | RamattraMapper 实例变量 |
| GestureEvent 队列 | 单帧消费完清空 | GestureRecognizer 实例变量 |

### 配置参数存储

所有可调参数集中在 `config.py`，以具名常量形式定义，无需数据库：

```
CAMERA_ID            = 0
TARGET_FPS           = 30
DEBOUNCE_FRAMES      = 4        # 去抖帧数（133ms @ 30fps）
EXTEND_THRESHOLD     = 8000     # 手掌面积阈值（像素²），需据摄像头分辨率标定
ZONE_TOP_BOUNDARY    = 0.35     # 画面高度归一化，y < 此值为 TOP 区域
ZONE_BOTTOM_BOUNDARY = 0.65     # y > 此值为 BOTTOM 区域
SWIPE_MIN_VELOCITY   = 0.03     # 甩手触发最小速度（归一化坐标/帧）
```

---

## 七、可观测性设计

### 实时 HUD（开发与演示均启用）

HUDRenderer 在每帧画面上叠加以下信息：

```
┌──────────────────────────────────────────┐
│  Hero: Moira                             │
│  Left:  EXTENDED  →  [LMB HOLD]         │
│  Right: RETRACTED →  -                  │
│  Last Event: LEFT_EXTEND                 │
│  Latency: 42ms                           │
│  FPS: 28                                 │
└──────────────────────────────────────────┘
```

### 延迟测量

- `GestureEvent` 携带触发时间戳
- `InputController` 执行完毕后记录完成时间戳
- 两者差值即为**手势识别到指令注入的端到端延迟**，实时显示在 HUD

### 控制台日志

开发阶段启用，生产演示时关闭。格式：

```
[FRAME 1042] LEFT_EXTEND fired → MOUSE_DOWN(left) | latency=38ms
[FRAME 1043] stable_frames=1 (candidate: RIGHT_ZONE_TOP)
```

日志级别通过 `config.py` 中的 `DEBUG_LOG = True/False` 控制，不引入额外日志库。
