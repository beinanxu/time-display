# -*- coding: utf-8 -*-
"""
时间显示器 (Time Display)
=========================

一个安静、常驻桌面最上层的多功能时间显示器，三种模式：

  CLOCK      时钟    —— 时间 + 日期
  TIMER      定时    —— 倒计时（默认 25 分钟），到点响铃 + 可语音播报
  STOPWATCH  秒表    —— 正计时，支持计次（Lap）

设计原则：不做任何评判、不弹警告、不闪烁。就一块安静的玻璃面板。

用法
----
  python app.py                 # 默认时钟模式，默认位置右上角
  python app.py --mode timer --minutes 25
  python app.py --mode stopwatch
  python app.py --probe         # 自检：把窗口位置和屏幕实际像素写进 _probe.txt

快捷键
------
  点击顶部模式名 / Tab         切换模式
  空格                         定时、秒表：开始 / 暂停
  R                            复位
  L                            秒表计次
  ↑ / ↓                        定时：±1 分钟（Shift 为 ±5 分钟）
  双击面板                     临时隐藏 / 显示
  Ctrl+Alt+A                   全局：循环切换模式（全屏程序里也生效）
  Ctrl+Alt+S                   全局：开始 / 暂停
  Ctrl+Alt+R                   全局：复位

所有外观和默认值都在 config.py 里改。
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import os
import sys
import time
import tkinter as tk
from tkinter import font as tkfont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import utils  # noqa: E402
from config import Config  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
VK = {"A": 0x41, "S": 0x53, "R": 0x52, "T": 0x54, "C": 0x43}
MODS = {"CTRL": utils.MOD_CONTROL, "ALT": utils.MOD_ALT, "SHIFT": utils.MOD_SHIFT}


def parse_hotkey(text, default_key="A"):
    """'Ctrl+Alt+A' -> (修饰键掩码, 虚拟键码)"""
    mods = 0
    vk = VK[default_key]
    for part in str(text).split("+"):
        p = part.strip().upper()
        if p in MODS:
            mods |= MODS[p]
        elif p in VK:
            vk = VK[p]
    return mods, vk


def hms(seconds, tenths=True):
    """秒 -> mm:ss 或 mm:ss.c（用于定时器）"""
    if seconds < 0:
        seconds = 0
    if tenths:
        total = int(seconds * 10)
        return "{:02d}:{:02d}.{}".format(total // 600, (total // 10) % 60, total % 10)
    total = int(seconds)
    return "{:02d}:{:02d}".format(total // 60, total % 60)


def csec(seconds):
    """秒 -> m:ss.cc（用于秒表）"""
    if seconds < 0:
        seconds = 0
    total = int(seconds * 100)
    cs = total % 100
    s = (total // 100) % 60
    m = total // 6000
    return "{}:{:02d}.{:02d}".format(m, s, cs)


class ClockApp:
    def __init__(self, mode):
        self.cfg = Config()
        self.mode = mode
        self.hotkeys_enabled = True
        self.next_custom_id = 0x7000

        # 定时
        self.timer_remaining = float(self.cfg.TIMER_MINUTES) * 60.0
        self.timer_deadline = None
        self.timer_finished_at = 0.0

        # 秒表
        self.sw_elapsed = 0.0
        self.sw_last_tick = None
        self.laps = []

        self._last_second = -1
        self._last_text = None
        self.hidden = False
        self._drag = None

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(self.cfg.APP_NAME)
        utils.try_icon(self.root, os.path.join(HERE, "icon.ico"))

        self.f_time = tkfont.Font(family=self.cfg.TIME_FONT,
                                  size=int(self.cfg.TIME_SIZE), weight="bold")
        self.f_date = tkfont.Font(family=self.cfg.DATE_FONT,
                                  size=int(self.cfg.DATE_SIZE))
        self.f_sub = tkfont.Font(family=self.cfg.DATE_FONT,
                                 size=int(self.cfg.SUB_SIZE))
        self.f_tab = tkfont.Font(family=self.cfg.DATE_FONT,
                                 size=int(self.cfg.DATE_SIZE), weight="bold")
        self.f_hint = tkfont.Font(family=self.cfg.DATE_FONT,
                                  size=int(self.cfg.HINT_SIZE))

        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()

        self.build()
        self.apply_mode(initial=True)
        self.begin_hotkeys()

        self.root.after(200, lambda: utils.reassert_top(self.win))
        self.root.after(1500, self.keep_on_top)
        self.root.after(50, self.tick)

    # ------------------------------------------------------------ 界面
    def build(self):
        bg = self.cfg.BG
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            self.win.attributes("-toolwindow", True)
        except Exception:
            pass
        self.win.configure(bg=bg)

        self.border = tk.Frame(self.win, bg=self.cfg.BORDER)
        self.border.pack(fill="both", expand=True, padx=self.cfg.PAD, pady=self.cfg.PAD)
        self.body = tk.Frame(self.border, bg=bg)
        self.body.pack(fill="both", expand=True)

        tabs = tk.Frame(self.body, bg=bg)
        tabs.pack(anchor="center", pady=(8, 0))
        self.tab_labels = {}
        for key, text in (("clock", "时钟"), ("timer", "定时"), ("stopwatch", "秒表")):
            lab = tk.Label(tabs, text=text, font=self.f_tab, bg=bg, fg=self.cfg.FG_DIM,
                           padx=7, cursor="hand2")
            lab.pack(side="left")
            lab.bind("<Button-1>", lambda e, k=key: self.switch_mode(k))
            self.tab_labels[key] = lab

        self.lbl_time = tk.Label(self.body, text="00:00:00", font=self.f_time,
                                 bg=bg, fg=self.cfg.FG)
        self.lbl_time.pack(anchor="center", padx=18, pady=(2, 0))

        self.lbl_sub = tk.Label(self.body, text="", font=self.f_date,
                                bg=bg, fg=self.cfg.FG_DIM)
        self.lbl_sub.pack(anchor="center", padx=18, pady=(0, 2))

        self.lbl_hint = tk.Label(self.body, text="", font=self.f_hint,
                                 bg=bg, fg=self.cfg.FG_HINT)
        self.lbl_hint.pack(anchor="center", padx=18, pady=(0, 8))

        for w in (self.win, self.border, self.body, self.lbl_time,
                  self.lbl_sub, self.lbl_hint):
            w.bind("<ButtonPress-1>", self.drag_start)
            w.bind("<B1-Motion>", self.drag_move)
            w.bind("<Double-Button-1>", self.toggle_hide)

        self.root.bind_all("<Tab>", lambda e: self.cycle_mode())
        self.root.bind_all("<space>", lambda e: self.toggle_run())
        self.root.bind_all("<Key-r>", lambda e: self.reset())
        self.root.bind_all("<Key-R>", lambda e: self.reset())
        self.root.bind_all("<Key-l>", lambda e: self.lap())
        self.root.bind_all("<Key-L>", lambda e: self.lap())
        self.root.bind_all("<Up>", lambda e: self.add_minutes(1))
        self.root.bind_all("<Down>", lambda e: self.add_minutes(-1))
        self.root.bind_all("<Shift-Up>", lambda e: self.add_minutes(5))
        self.root.bind_all("<Shift-Down>", lambda e: self.add_minutes(-5))
        self.root.bind_all("<Escape>", lambda e: self.reset())

        self.relayout()

    def relayout(self):
        self.win.update_idletasks()
        w = max(self.cfg.MIN_WIDTH, self.win.winfo_reqwidth())
        h = self.win.winfo_reqheight()
        x = self.cfg.X
        y = self.cfg.Y
        if x is None:
            x = max(0, self.sw - w - self.cfg.MARGIN)
        if y is None:
            y = self.cfg.MARGIN_TOP
        if self._drag:
            x, y = self._drag
        self.win.geometry("{}x{}+{}+{}".format(w, h, int(x), int(y)))
        self._drag = (int(x), int(y))

    # ------------------------------------------------------------ 模式
    def switch_mode(self, key):
        if key == self.mode:
            return
        self.mode = key
        self.apply_mode()

    def cycle_mode(self):
        order = ["clock", "timer", "stopwatch"]
        self.switch_mode(order[(order.index(self.mode) + 1) % len(order)])

    def apply_mode(self, initial=False):
        bg = self.cfg.BG
        for key, lab in self.tab_labels.items():
            active = key == self.mode
            lab.configure(fg=self.cfg.FG_ACCENT if active else self.cfg.FG_DIM)
        if self.mode == "clock":
            self.lbl_time.configure(fg=self.cfg.FG, font=self.f_time)
            self.lbl_hint.configure(text="双击隐藏 · Tab 切换 · Ctrl+Alt+A 全局切换")
        elif self.mode == "timer":
            self.lbl_time.configure(fg=self.cfg.FG_TIMER, font=self.f_time)
            self.lbl_hint.configure(text="空格 开始/暂停 · R 复位 · ↑↓ 调整分钟")
        else:
            self.lbl_time.configure(fg=self.cfg.FG_STOPWATCH, font=self.f_time)
            self.lbl_hint.configure(text="空格 开始/暂停 · L 计次 · R 复位")
        self.lbl_time.configure(bg=bg)
        self.relayout()

    # ------------------------------------------------------------ 主循环
    def tick(self):
        now = time.time()
        mono = time.monotonic()
        finished = False

        if self.mode == "stopwatch" and self.sw_last_tick is not None:
            self.sw_elapsed += mono - self.sw_last_tick
            self.sw_last_tick = mono

        if self.mode == "timer" and self.timer_deadline is not None:
            if mono >= self.timer_deadline:
                self.timer_remaining = 0.0
                self.timer_deadline = None
                self.timer_finished_at = now
                finished = True

        text, sub = self.compose(now, mono)
        if text != self._last_text or self._last_second != time.localtime().tm_sec:
            self.lbl_time.configure(text=text)
            self.lbl_sub.configure(text=sub)
            self._last_text = text
            self._last_second = time.localtime().tm_sec

        if finished:
            self.on_finish()

        self.root.after(50, self.tick)

    def compose(self, now, mono):
        lt = time.localtime(now)
        if self.mode == "clock":
            fmt = "%H:%M:%S" if self.cfg.SHOW_SECONDS else "%H:%M"
            return time.strftime(fmt, lt), self.date_text(lt)

        if self.mode == "timer":
            left = (self.timer_deadline - mono) if self.timer_deadline is not None \
                else self.timer_remaining
            state = "运行中" if self.timer_deadline is not None else (
                "已暂停" if 0 < left < self.timer_remaining or left == 0 else "待开始")
            if left <= 0 and self.timer_finished_at:
                return "00:00.0", "时间到！空格重置，↑↓ 改时长"
            return hms(left), "倒计时 · {}".format(
                "运行中" if self.timer_deadline is not None else "已暂停")

        return csec(self.sw_elapsed), self.stopwatch_sub()

    def stopwatch_sub(self):
        running = "运行中" if self.sw_last_tick is not None else "已暂停"
        if not self.laps:
            return "秒表 · {}".format(running)
        last = self.laps[-1]
        return "秒表 · {} · 第{}次 {}（差 +{}）".format(
            running, len(self.laps), csec(last["total"]), csec(last["delta"]))

    @staticmethod
    def date_text(lt):
        fmt = Config.DATE_FORMAT
        weekday = WEEKDAY_CN[lt.tm_wday]
        fmt = fmt.replace("%A", weekday)   # strftime 的 %A 跟系统语言有关，不用它
        try:
            return time.strftime(fmt, lt)
        except Exception:
            return "{}年{}月{}日 {}".format(
                lt.tm_year, lt.tm_mon, lt.tm_mday, weekday)

    # ------------------------------------------------------------ 操作
    def on_finish(self):
        if self.cfg.SOUND:
            utils.beep(times=3, freq=880)
        if self.cfg.TTS:
            utils.say(self.cfg.TTS_TEXT)
        self.lbl_time.configure(fg=self.cfg.FG_ALERT)
        self.root.after(1200, lambda: self.lbl_time.configure(fg=self.cfg.FG_TIMER))

    def toggle_run(self):
        mono = time.monotonic()
        if self.mode == "stopwatch":
            if self.sw_last_tick is None:
                self.sw_last_tick = mono
            else:
                self.sw_elapsed += mono - self.sw_last_tick
                self.sw_last_tick = None
        elif self.mode == "timer":
            if self.timer_deadline is not None:
                self.timer_remaining = max(0.0, self.timer_deadline - mono)
                self.timer_deadline = None
            else:
                if self.timer_remaining <= 0:
                    self.timer_remaining = self.cfg.TIMER_MINUTES * 60.0
                self.timer_finished_at = 0.0
                self.timer_deadline = mono + self.timer_remaining
        elif self.mode == "clock":
            self.cycle_mode()

    def reset(self):
        if self.mode == "timer":
            self.timer_deadline = None
            self.timer_remaining = float(self.cfg.TIMER_MINUTES) * 60.0
            self.timer_finished_at = 0.0
            self.lbl_time.configure(fg=self.cfg.FG_TIMER)
        elif self.mode == "stopwatch":
            self.sw_elapsed = 0.0
            self.sw_last_tick = None
            self.laps = []
        self._last_text = None

    def lap(self):
        if self.mode != "stopwatch":
            return
        total = self.sw_elapsed
        prev = self.laps[-1]["total"] if self.laps else 0.0
        self.laps.append({"total": total, "delta": total - prev})
        self._last_text = None

    def add_minutes(self, delta):
        if self.mode != "timer":
            return
        base = self.timer_remaining if self.timer_deadline is None else \
            max(0.0, self.timer_deadline - time.monotonic())
        base = max(0.0, base + delta * 60.0)
        self.timer_remaining = base
        if self.timer_deadline is not None:
            self.timer_deadline = time.monotonic() + base
        self._last_text = None

    def toggle_hide(self, _e=None):
        self.hidden = not self.hidden
        if self.hidden:
            self.win.withdraw()
        else:
            self.win.deiconify()
            utils.reassert_top(self.win)

    # ------------------------------------------------------------ 拖动 / 置顶
    def drag_start(self, e):
        self._dx, self._dy = e.x_root, e.y_root
        self._gx, self._gy = self.win.winfo_x(), self.win.winfo_y()

    def drag_move(self, e):
        nx = self._gx + (e.x_root - self._dx)
        ny = self._gy + (e.y_root - self._dy)
        self._drag = (nx, ny)
        self.win.geometry("+{}+{}".format(nx, ny))

    def keep_on_top(self):
        if not self.hidden:
            utils.reassert_top(self.win)
            self._ticks = getattr(self, "_ticks", 0) + 1
            if self._ticks % 8 == 0:
                utils.nudge_topmost(self.win)
        self.root.after(1500, self.keep_on_top)

    # ------------------------------------------------------------ 全局热键
    def bind_global(self, hid, keys, handler):
        def fire(_hid=hid):
            self.root.after(0, handler)
        return hid, keys, fire

    def begin_hotkeys(self):
        if not self.cfg.HOTKEY_ENABLE:
            return
        bindings = {}
        self.global_handlers = {}
        specs = [
            (1, self.cfg.HOTKEY_CYCLE, self.cycle_mode, "cycle"),
            (2, self.cfg.HOTKEY_TOGGLE, self.toggle_run, "toggle"),
            (3, self.cfg.HOTKEY_RESET, self.reset, "reset"),
        ]
        used = set()
        for hid, text, handler, _name in specs:
            mods, vk = parse_hotkey(text)
            while hid in used:
                hid = self.next_custom_id
                self.next_custom_id += 1
            used.add(hid)
            bindings[hid] = (mods, vk)
            self.global_handlers[hid] = handler

        hid_map = list(bindings)
        orig = dict(bindings)

        def on_event(hid):
            # utils 的循环会轮换同一个键位给不同窗口，这里先做一次可用性探测
            h = self.global_handlers.get(hid)
            if h is None:
                return
            try:
                self.root.after(0, h)
            except Exception:
                pass

        import threading
        threading.Thread(target=utils.hotkey_loop,
                         args=(orig, on_event), daemon=True).start()

    # ------------------------------------------------------------ 运行
    def run(self):
        self.root.mainloop()

    def destroy(self):
        try:
            self.root.destroy()
        except Exception:
            pass


def probe(mode="clock"):
    """自检：报告窗口位置 + 那个位置屏幕上真实的像素，用来判断是否被全屏程序遮住。"""
    app = ClockApp(mode)
    log_path = os.path.join(HERE, "_probe.txt")

    def dump():
        try:
            app.root.update_idletasks()
            hwnd = utils.hwnd_of(app.win)
            r = wt.RECT()
            utils.user32.GetWindowRect(hwnd, ctypes.byref(r))
            lines = [
                "hwnd={}".format(hwnd),
                "rect=({},{},{}) 尺寸 {}x{}".format(
                    r.left, r.top, r.right, r.bottom,
                    r.right - r.left, r.bottom - r.top),
                "设置底色={}".format(app.win.cget("bg")),
                "屏幕尺寸={}x{}".format(app.sw, app.sh),
                "屏幕实际像素:",
            ]
            hdc = utils.user32.GetDC(0)
            for dx, dy in ((3, 3), (14, 14), ((r.right - r.left) // 2,
                                              (r.bottom - r.top) // 2)):
                v = ctypes.windll.gdi32.GetPixel(hdc, r.left + dx, r.top + dy)
                lines.append("  (+{},+{}) = {}".format(
                    dx, dy, (v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF)))
            utils.user32.ReleaseDC(0, hdc)
            lines.append("")
            lines.append("如果上面的像素值 ≈ 设置底色，说明窗口真的显示在最上层。")
            lines.append("如果像素是别的东西（游戏/视频），说明你的桌面合成没有把置顶窗口画出来，")
            lines.append("把全屏程序改成「窗口化 / 无边框窗口」即可解决。")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception as e:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("probe error: {!r}\n".format(e))
        finally:
            app.root.after(150, app.destroy)

    app.root.after(1200, dump)
    app.run()


def main():
    ap = argparse.ArgumentParser(description="桌面时间显示器：时钟 / 定时 / 秒表")
    ap.add_argument("--mode", choices=["clock", "timer", "stopwatch"], default=None)
    ap.add_argument("--minutes", type=float, default=None, help="定时模式的分钟数")
    ap.add_argument("--probe", action="store_true", help="自检并写出 _probe.txt")
    args = ap.parse_args()

    if args.probe:
        probe(args.mode or "clock")
        return

    app = ClockApp(args.mode or Config().START_MODE)
    if args.minutes is not None:
        app.timer_remaining = max(0.0, args.minutes * 60.0)
    print("时间显示器已启动，模式 = {}".format(app.mode))
    app.run()


if __name__ == "__main__":
    main()
