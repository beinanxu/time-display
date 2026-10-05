# -*- coding: utf-8 -*-
"""
设置界面 (Settings)
===================

一个 tkinter 小窗口，改完点「保存」直接写回 config.py（只替换等号右边的值，
注释和排版原样保留）。

打开方式：
  - 在时间显示器面板上按 Ctrl+Alt+,     （全局热键，游戏里也能开）
  - 命令行：python settings.py

不依赖主程序，可以单独运行来改配置。
"""

import os
import re
import sys
import tkinter as tk
from tkinter import font as tkfont, messagebox

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.py")

# 界面配色，跟主面板保持一致
BG = "#131316"
CARD = "#1B1B21"
BORDER = "#2C2C34"
FG = "#EDEDF2"
FG_DIM = "#8A8A99"
ACCENT = "#6FA8FF"
WARN = "#FFB454"


def fmt_py(value):
    """把 Python 值写成 config.py 里的字面量。"""
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, str):
        return '"{}"'.format(value.replace('"', '\\"'))
    return repr(value)


class ConfigWriter:
    """用正则只改等号右边的值，保住文件里所有注释。"""

    def __init__(self, path=CONFIG_PATH):
        self.path = path

    def apply(self, changes):
        """changes: {属性名: 新值}；返回实际被改动的属性名列表。"""
        with open(self.path, "r", encoding="utf-8") as f:
            src = f.read()
        text = src
        changed = []
        for key, value in changes.items():
            pattern = re.compile(
                r"^([ \t]*" + re.escape(key) + r"[ \t]*=[ \t]*)([^\r\n#]*)",
                re.MULTILINE)

            def repl(m, value=value):
                return m.group(1) + fmt_py(value) + "  "

            new_text, n = pattern.subn(repl, text, count=1)
            if n:
                text = new_text
                changed.append(key)
        if text != src:
            # 写之前先备份一份
            try:
                with open(self.path + ".bak", "w", encoding="utf-8") as f:
                    f.write(src)
            except Exception:
                pass
            with open(self.path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
        return changed


class Row:
    """一行设置。kind: check / spin / text"""

    def __init__(self, key, label, kind, extra=None, hint="", section=None,
                 live=True):
        self.key = key
        self.label = label
        self.kind = kind
        self.extra = extra or {}
        self.hint = hint
        self.section = section
        self.live = live          # 只影响界面刷新时是否立刻能看出效果


ROWS = [
    Row("SHOW_WALL_CLOCK", "秒表 / 定时 下面显示当前时间", "check", section="显示",
        hint="副标题里附上挂钟时间，例如 14:23:07 · 运行中"),
    Row("SHOW_SECONDS", "时钟显示秒", "check"),
    Row("DATE_FORMAT", "时钟日期格式", "text", section="显示",
        extra={"width": 22}, hint='%A 会替换成 周一/周二…，例：%Y年%m月%d日 %A'),

    Row("SOUND", "定时到点响铃", "check", section="提醒"),
    Row("TTS", "定时到点语音念一句", "check"),
    Row("TTS_TEXT", "语音内容", "text", extra={"width": 22}),

    Row("TIMER_MINUTES", "定时默认分钟数", "spin", section="计时",
        extra={"from": 1, "to": 600}),
    Row("NODE_ROWS", "打点面板显示几个节点", "spin", extra={"from": 1, "to": 8}),

    Row("HOTKEY_STOPWATCH", "秒表 一键启停", "text", section="全局热键",
        extra={"width": 18}, hint="改完需要重启程序生效"),
    Row("HOTKEY_TIMER", "定时 一键启停", "text", extra={"width": 18}),
    Row("HOTKEY_MARK", "打点 / 标记一个点", "text", extra={"width": 18}),
    Row("HOTKEY_CYCLE", "循环切换模式", "text", extra={"width": 18}),
    Row("HOTKEY_SETTINGS", "打开本设置界面", "text", extra={"width": 18}),
    Row("HOTKEY_ENABLE", "启用全局热键", "check"),
]


class SettingsDialog:
    def __init__(self, master=None, host=None, config_module=None):
        self.host = host
        # 允许传 Config 类或 Config 实例，统一成实例用
        if isinstance(config_module, type):
            config_module = config_module()
        self.config_module = config_module
        self.vars = {}
        self.spinboxes = {}
        self.changed = False

        self.top = tk.Toplevel(master) if master is not None else tk.Tk()
        self.top.title("时间显示器 · 设置")
        self.top.configure(bg=BG)
        self.top.attributes("-topmost", True)
        self.top.resizable(False, False)

        try:
            ico = os.path.join(HERE, "icon.ico")
            if os.path.exists(ico):
                self.top.iconbitmap(ico)
        except Exception:
            pass

        self.build()

        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self.top.bind("<Escape>", lambda e: self.close())
        self.center()

    # ---------------------------------------------------------------- 界面
    def build(self):
        title = tk.Label(self.top, text="时间显示器 · 设置", bg=BG, fg=FG,
                         font=("Microsoft YaHei", 13, "bold"))
        title.pack(anchor="w", padx=18, pady=(16, 2))
        tk.Label(self.top, text="勾选或修改后点「保存」，直接写回 config.py",
                 bg=BG, fg=FG_DIM, font=("Microsoft YaHei", 9)).pack(
            anchor="w", padx=18, pady=(0, 10))

        body = tk.Frame(self.top, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        for row in ROWS:
            if row.section:
                tk.Label(body, text=row.section, bg=BG, fg=ACCENT,
                         font=("Microsoft YaHei", 9, "bold")).pack(
                    anchor="w", padx=6, pady=(10, 2))
            self.add_row(body, row)

        bar = tk.Frame(self.top, bg=BG)
        bar.pack(fill="x", padx=18, pady=(4, 16))
        tk.Button(bar, text="保存", command=self.save, width=10,
                  bg=ACCENT, fg="#0B0B0E", activebackground="#8FC0FF",
                  relief="flat", font=("Microsoft YaHei", 10, "bold")).pack(side="right")
        tk.Button(bar, text="取消", command=self.close, width=8,
                  bg=CARD, fg=FG, activebackground=BORDER,
                  relief="flat").pack(side="right", padx=8)
        tk.Button(bar, text="恢复默认", command=self.restore_defaults, width=10,
                  bg=CARD, fg=WARN, activebackground=BORDER,
                  relief="flat").pack(side="left")
        self.status = tk.Label(bar, text="", bg=BG, fg=FG_DIM,
                               font=("Microsoft YaHei", 9))
        self.status.pack(side="left", padx=10)

    def add_row(self, parent, row):
        value = getattr(self.config_module, row.key, None)
        card = tk.Frame(parent, bg=CARD)
        card.pack(fill="x", padx=4, pady=2)
        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill="x", padx=10, pady=7)

        left = tk.Frame(inner, bg=CARD)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=row.label, bg=CARD, fg=FG,
                 font=("Microsoft YaHei", 10)).pack(anchor="w")
        if row.hint:
            tk.Label(left, text=row.hint, bg=CARD, fg=FG_DIM,
                     font=("Microsoft YaHei", 8)).pack(anchor="w")

        if row.kind == "check":
            var = tk.BooleanVar(value=bool(value))
            tk.Checkbutton(inner, variable=var, bg=CARD, activebackground=CARD,
                           selectcolor=CARD, highlightthickness=0,
                           bd=0).pack(side="right")
        elif row.kind == "spin":
            self._last_spin = row.key      # 诊断用：确认走到哪一行
            var = tk.IntVar(value=int(value) if value is not None else 0)
            kw = dict(from_=int(row.extra.get("from", 0)),
                      to=int(row.extra.get("to", 999)),
                      width=6, textvariable=var, bg=CARD, fg=FG, relief="flat",
                      buttonbackground=BORDER, highlightthickness=0,
                      insertbackground=FG, justify="center")
            # 注意：属性名不能叫 self.spin —— Spinbox 自带 spin() 方法，会被覆盖
            self.spinboxes[row.key] = tk.Spinbox(inner, **kw)
            self.spinboxes[row.key].pack(side="right")
        else:
            var = tk.StringVar(value="" if value is None else str(value))
            tk.Entry(inner, textvariable=var, width=row.extra.get("width", 20),
                     bg="#0E0E11", fg=FG, relief="flat", insertbackground=FG,
                     highlightthickness=1, highlightbackground=BORDER,
                     highlightcolor=ACCENT).pack(side="right")
        self.vars[row.key] = (var, row)

    def center(self):
        self.top.update_idletasks()
        w = max(440, self.top.winfo_reqwidth())
        h = self.top.winfo_reqheight()
        x = (self.top.winfo_screenwidth() - w) // 2
        y = max(20, (self.top.winfo_screenheight() - h) // 3)
        self.top.geometry("{}x{}+{}+{}".format(w, h, x, y))

    # ---------------------------------------------------------------- 动作
    def collect(self):
        changes = {}
        for key, (var, row) in self.vars.items():
            value = var.get()
            if row.kind == "check":
                value = bool(value)
            elif row.kind == "spin":
                try:
                    value = int(value)
                except Exception:
                    continue
            else:
                value = str(value).strip()
                if row.key != "DATE_FORMAT" and not value:
                    continue
                if row.key == "DATE_FORMAT":
                    value = value or "%Y年%m月%d日 %A"
            changes[key] = value
        return changes

    def save(self):
        changes = self.collect()
        try:
            changed = ConfigWriter().apply(changes)
        except Exception as exc:
            messagebox.showerror("保存失败", "写入 config.py 出错：\n{}".format(exc),
                                 parent=self.top)
            return
        # 热键列表需要重启才能重新注册
        hotkey_changed = any(k.startswith("HOTKEY_") for k in changed)
        # 立刻把能生效的项应用到正在运行的实例上
        live = 0
        for key, value in changes.items():
            try:
                setattr(self.config_module, key, value)
                live += 1
            except Exception:
                pass
        if self.host is not None:
            try:
                self.host.relayout()
            except Exception:
                pass
        self.changed = True
        msg = "已保存 {} 项到 config.py".format(len(changed))
        if hotkey_changed:
            msg += "（热键改动需重启程序生效）"
        self.status.configure(text=msg, fg=ACCENT)
        self.top.after(900, self.close)

    def restore_defaults(self):
        if not messagebox.askyesno(
                "恢复默认",
                "把界面上的选项恢复成默认值？\n（还是要点「保存」才会写到文件）",
                parent=self.top):
            return
        defaults = {
            "SHOW_WALL_CLOCK": True, "SHOW_SECONDS": True,
            "DATE_FORMAT": "%Y年%m月%d日 %A",
            "SOUND": True, "TTS": False, "TTS_TEXT": "时间到，休息一下",
            "TIMER_MINUTES": 25, "NODE_ROWS": 3,
            "HOTKEY_STOPWATCH": "Ctrl+Alt+1", "HOTKEY_TIMER": "Ctrl+Alt+2",
            "HOTKEY_MARK": "Ctrl+Alt+M", "HOTKEY_CYCLE": "Ctrl+Alt+A",
            "HOTKEY_SETTINGS": "Ctrl+Alt+,", "HOTKEY_ENABLE": True,
        }
        for key, value in defaults.items():
            if key in self.vars:
                var, row = self.vars[key]
                var.set(value)
        self.status.configure(text="已填入默认值，点「保存」才会写入", fg=WARN)

    def close(self):
        if self.host is None:
            try:
                self.top.destroy()
            except Exception:
                pass
        else:
            try:
                self.top.destroy()
            except Exception:
                pass


# -------------------------------------------------------------------- 入口
def open_dialog(host):
    """给主程序调用：打开设置窗口。"""
    import config as config_module
    try:
        if getattr(host, "_settings_dialog", None) is not None:
            dlg = host._settings_dialog
            if dlg.top.winfo_exists():
                dlg.top.lift()
                dlg.top.focus_force()
                return dlg
    except Exception:
        pass
    dlg = SettingsDialog(master=host.root, host=host, config_module=config_module)
    host._settings_dialog = dlg
    return dlg


def main():
    import config as config_module
    dlg = SettingsDialog(master=None, host=None, config_module=config_module)
    dlg.top.mainloop()


if __name__ == "__main__":
    main()
