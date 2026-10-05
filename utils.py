# -*- coding: utf-8 -*-
"""Win32 小工具：置顶、图标、全局热键、系统提示音、语音。"""

import ctypes
import ctypes.wintypes as wt
import subprocess
import threading
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001

REDRAW_FLAGS = 0x0001 | 0x0004 | 0x0080 | 0x0100 | 0x0400


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wt.HWND),
        ("message", wt.UINT),
        ("wParam", wt.WPARAM),
        ("lParam", wt.LPARAM),
        ("time", wt.DWORD),
        ("pt_x", wt.LONG),
        ("pt_y", wt.LONG),
    ]


def hwnd_of(win):
    """Tk 的 frame() 可能是 int，也可能是 '0x...' 字符串。"""
    raw = win.frame()
    if raw is None:
        raw = win.winfo_id()
    if isinstance(raw, str):
        return int(raw, 16) if raw.lower().startswith("0x") else int(raw)
    return int(raw)


def try_icon(root, path):
    import os
    if os.path.exists(path):
        try:
            root.iconbitmap(path)
        except Exception:
            pass


def reassert_top(win):
    """用 Win32 把窗口顶到最上层（对付会抢顶层的全屏程序）。"""
    try:
        hwnd = hwnd_of(win)
        if not hwnd:
            return
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex = (ex | WS_EX_TOOLWINDOW) & ~WS_EX_NOACTIVATE
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
    except Exception:
        try:
            win.attributes("-topmost", True)
            win.lift()
        except Exception:
            pass


def nudge_topmost(win):
    """摘掉 topmost 再戴上，逼桌面合成器重画一次。"""
    try:
        hwnd = hwnd_of(win)
        if not hwnd:
            return
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        user32.RedrawWindow(hwnd, None, None, REDRAW_FLAGS)
    except Exception:
        pass


# ---------------------------------------------------------------- 全局热键
def hotkey_loop(bindings, on_event):
    """在独立线程里注册全局热键，支持一个键位被多个窗口循环使用。

    bindings: {热键ID: (修饰键, 虚拟键码)}
    on_event: 回调，收到热键 ID
    """
    ids = list(bindings)
    registered = set()
    last = None

    def register_all():
        for hid in ids:
            mods, vk = bindings[hid]
            if user32.RegisterHotKey(None, hid, mods | MOD_NOREPEAT, vk):
                registered.add(hid)

    register_all()
    msgs = {}
    msg = MSG()
    while True:
        if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
            if msg.message == WM_HOTKEY:
                hid = int(msg.wParam)
                if hid in ids:
                    last = hid
                    order = [ids.index(h) for h in registered]
                    if order:
                        nxt = ids[(order[-1] + 1) % len(ids)]
                        if nxt not in registered:
                            nxt = ids[min(order)]
                        for h in list(registered):
                            user32.UnregisterHotKey(None, h)
                        registered.clear()
                        mods, vk = bindings[nxt]
                        if user32.RegisterHotKey(None, nxt, mods | MOD_NOREPEAT, vk):
                            registered.add(nxt)
                    try:
                        on_event(last)
                    except Exception:
                        pass
        time.sleep(0.1)


# ---------------------------------------------------------------- 声音
def beep(times=3, freq=880):
    def run():
        try:
            import winsound
            for i in range(times):
                winsound.Beep(freq + i * 220, 180)
                time.sleep(0.05)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


def say(text):
    """用系统语音念一句（Windows SAPI）。"""
    def run():
        try:
            safe = (text.replace("'", "").replace('"', "")
                    .replace("\n", "，").replace("\r", ""))
            ps = ("Add-Type -AssemblyName System.Speech;"
                  "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                  f"$s.Speak('{safe}')")
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                creationflags=0x08000000,
            )
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()
