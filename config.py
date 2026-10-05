# -*- coding: utf-8 -*-
"""
时间显示器 —— 配置

改完保存，重启程序生效。颜色用 #RRGGBB。
"""


class Config:
    APP_NAME = "时间显示器"

    # ---------------- 位置与尺寸 ----------------
    X = None          # None = 自动贴右边；也可以写 X = 1450
    Y = None          # None = 距顶部 MARGIN_TOP
    MARGIN = 24       # 自动贴边时距屏幕右边的像素
    MARGIN_TOP = 40
    MIN_WIDTH = 240
    PAD = 2           # 外框粗细

    # ---------------- 配色 ----------------
    BG = "#131316"          # 面板背景
    BORDER = "#2C2C34"      # 外框
    FG = "#EDEDF2"          # 时钟数字
    FG_DIM = "#8A8A99"      # 日期 / 未选中的模式名
    FG_HINT = "#5A5A68"     # 底部提示
    FG_ACCENT = "#6FA8FF"   # 当前模式高亮
    FG_TIMER = "#FFB454"    # 定时数字
    FG_STOPWATCH = "#7DE0B0"  # 秒表数字
    FG_MARK = "#C79BFF"     # 打点数字
    FG_NODE = "#8A8A99"     # 节点列表
    FG_ALERT = "#FF5C5C"    # 定时到点的数字

    # ---------------- 字体 ----------------
    TIME_FONT = "Consolas"    # 等宽，数字跳动不会左右晃
    TIME_SIZE = 40
    DATE_FONT = "Microsoft YaHei"
    DATE_SIZE = 11
    SUB_SIZE = 10
    HINT_SIZE = 9
    NODE_SIZE = 10          # 打点模式下节点列表的字号

    # ---------------- 行为 ----------------
    START_MODE = "mark"       # 命令行启动时的默认模式：clock / timer / stopwatch / mark
    SHOW_SECONDS = True
    DATE_FORMAT = "%Y年%m月%d日 %A"   # %A 会显示成 周一/周二…
    SHOW_WALL_CLOCK = True    # 秒表 / 定时 的副标题里是否附上当前挂钟时间
    SOUND = True              # 定时到点响铃
    TTS = False               # 定时到点用系统语音念一句
    TTS_TEXT = "时间到，休息一下"

    # ---------------- 打点 ----------------
    NODE_ROWS = 3             # 面板上最多显示几个最近的节点

    # ---------------- 定时 ----------------
    TIMER_MINUTES = 25        # 默认倒计时长度

    # ---------------- 全局热键 ----------------
    HOTKEY_ENABLE = True
    HOTKEY_CYCLE = "Ctrl+Alt+A"        # 循环切换模式
    HOTKEY_TOGGLE = "Ctrl+Alt+S"       # 开始 / 暂停（当前模式）
    HOTKEY_RESET = "Ctrl+Alt+R"        # 复位（当前模式）
    HOTKEY_MARK = "Ctrl+Alt+M"         # 打点
    HOTKEY_STOPWATCH = "Ctrl+Alt+1"    # 一键启停秒表
    HOTKEY_TIMER = "Ctrl+Alt+2"        # 一键启停定时
    HOTKEY_SETTINGS = "Ctrl+Alt+,"     # 打开设置界面
