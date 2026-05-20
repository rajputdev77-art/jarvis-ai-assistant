"""
JARVIS HUD — Mark VII (Phase 7.1)
Two modes:
  COMPACT  (default) — small floating widget, top-right, draggable, non-blocking.
  IMMERSIVE          — fullscreen Iron-Man HUD, Win+J to summon, ESC to dismiss.
Global hotkey: Win+J toggles immersive (works even when HUD is hidden).
"""

import os
import sys
import json
import math
import time
import random
import threading
from collections import deque
from datetime import datetime

from PyQt6.QtCore import (Qt, QTimer, QRectF, QPointF, pyqtSignal,
                          pyqtSlot, QPoint, QEvent)
from PyQt6.QtGui import (QPainter, QColor, QBrush, QPen, QFont, QPainterPath,
                         QLinearGradient, QRadialGradient, QPolygonF,
                         QFontMetrics, QKeySequence, QShortcut, QCursor)
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSizePolicy, QMenu)

EVENTS_FILE  = r"C:\Users\Dev\JARVIS\hud_events.jsonl"
PROJECT_FILE = r"C:\Users\Dev\JARVIS\project_index.json"

HOT_ROD_RED = QColor(190, 30, 40)
GOLD        = QColor(255, 195, 60)
PANEL_BG    = QColor(12, 16, 22, 235)
CYAN        = QColor(80, 220, 255)
WHITE       = QColor(235, 240, 250)
SUBTLE      = QColor(140, 150, 170)
GREEN       = QColor(80, 230, 120)

STATE_COLOURS = {
    "idle":      QColor(120, 130, 145),
    "listening": GREEN,
    "thinking":  GOLD,
    "speaking":  CYAN,
    "working":   HOT_ROD_RED,
}
STATE_LABEL = {
    "idle": "STANDBY", "listening": "LISTENING",
    "thinking": "REASONING", "speaking": "SPEAKING", "working": "EXECUTING",
}
AGENTS = ["THOR", "CAPTAIN", "HULK", "HAWKEYE", "WIDOW"]


# ─── ARC REACTOR ──────────────────────────────────────────────────
class ArcReactor(QWidget):
    def __init__(self, size=80):
        super().__init__()
        self.setMinimumSize(size, size)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.state = "idle"
        self.phase = 0.0
        self.amplitude = 0.2
        t = QTimer(self); t.timeout.connect(self._tick); t.start(40)

    def _tick(self):
        self.phase += 0.05
        self.amplitude = max(self.amplitude * 0.96, 0.18)
        self.update()

    def set_state(self, state):
        self.state = state
        if state == "speaking": self.amplitude = 1.0
        elif state == "listening": self.amplitude = 0.6
        elif state in ("thinking", "working"): self.amplitude = 0.45
        self.update()

    def pulse(self, s=0.8):
        self.amplitude = max(self.amplitude, s)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) * 0.38
        glow = STATE_COLOURS.get(self.state, CYAN)
        for i in range(5, 0, -1):
            rr = r + i * 10 * (1 + 0.4 * self.amplitude * math.sin(self.phase))
            c = QColor(glow); c.setAlpha(int(18 + 15 * (5 - i) / 5 * self.amplitude))
            p.setBrush(QBrush(c)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), rr, rr)
        # segmented ring
        segs = 9
        for i in range(segs):
            a1 = (i / segs) * 2 * math.pi + self.phase * 0.1
            a2 = ((i + 0.7) / segs) * 2 * math.pi + self.phase * 0.1
            r1 = r * 1.05; r2 = r * 0.88
            poly = QPolygonF([
                QPointF(cx + r1 * math.cos(a1), cy + r1 * math.sin(a1)),
                QPointF(cx + r1 * math.cos(a2), cy + r1 * math.sin(a2)),
                QPointF(cx + r2 * math.cos(a2 - 0.05), cy + r2 * math.sin(a2 - 0.05)),
                QPointF(cx + r2 * math.cos(a1 + 0.05), cy + r2 * math.sin(a1 + 0.05)),
            ])
            c = QColor(glow); c.setAlpha(180)
            p.setBrush(QBrush(c)); p.setPen(QPen(QColor(255, 255, 255, 30), 1))
            p.drawPolygon(poly)
        # gold rings
        p.setPen(QPen(GOLD, 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r * 0.85, r * 0.85)
        p.drawEllipse(QPointF(cx, cy), r * 0.7, r * 0.7)
        # core
        cr = r * 0.42 + 5 * self.amplitude * abs(math.sin(self.phase * 2))
        grad = QRadialGradient(cx, cy, cr)
        grad.setColorAt(0.0, QColor(255, 255, 255, 240))
        grad.setColorAt(0.4, QColor(glow.red(), glow.green(), glow.blue(), 220))
        grad.setColorAt(1.0, QColor(glow.red(), glow.green(), glow.blue(), 30))
        p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), cr, cr)


# ─── EVENT STREAM ─────────────────────────────────────────────────
class EventStream(QWidget):
    def __init__(self, max_events=18):
        super().__init__()
        self.events = deque(maxlen=max_events)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def add(self, kind, text):
        self.events.append((time.time(), kind, text))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        y = h - 8
        for ts, kind, text in reversed(self.events):
            age = time.time() - ts
            alpha = max(70, int(255 - age * 3))
            kc = {
                "user_said": GOLD, "speak": CYAN, "tool_call": HOT_ROD_RED,
                "tool_result": GREEN, "shell": QColor(255, 130, 60),
                "agent_start": QColor(200, 100, 240), "agent_done": GREEN,
                "window_focus": SUBTLE, "predictive": QColor(255, 215, 100),
            }
            kl = {
                "user_said": "YOU", "speak": "JRV", "tool_call": "TL",
                "tool_result": " ↳", "shell": "SH", "agent_start": "→",
                "agent_done": "←", "window_focus": "FW", "predictive": "PRD",
            }
            c = QColor(kc.get(kind, SUBTLE)); c.setAlpha(alpha)
            p.setPen(c); p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            p.drawText(6, y, kl.get(kind, kind[:3].upper()))
            tc = QColor(WHITE); tc.setAlpha(alpha)
            p.setPen(tc); p.setFont(QFont("Segoe UI", 8))
            fm = QFontMetrics(p.font())
            clip = fm.elidedText(text, Qt.TextElideMode.ElideRight, w - 36)
            p.drawText(28, y, clip)
            y -= 18
            if y < 16: break


# ─── AGENT MINI ROW ───────────────────────────────────────────────
class AgentRow(QWidget):
    def __init__(self):
        super().__init__()
        self.statuses = {a: "idle" for a in AGENTS}
        self.setFixedHeight(28)

    def update_agent(self, name, status):
        self.statuses[name] = status
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        slot = w / len(AGENTS)
        for i, a in enumerate(AGENTS):
            x = i * slot + slot / 2
            stat = self.statuses[a]
            c = HOT_ROD_RED if stat == "working" else GOLD if stat == "thinking" else GREEN if stat == "done" else SUBTLE
            p.setBrush(QBrush(c)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, 8), 4, 4)
            p.setPen(SUBTLE); p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
            fm = QFontMetrics(p.font())
            tw = fm.horizontalAdvance(a)
            p.drawText(int(x - tw / 2), 24, a)


# ─── COMPACT WIDGET (default mode — top-right, ~300x420) ──────────
class CompactHUD(QWidget):
    """Small always-on-top widget that doesn't block the screen."""
    requestImmersive = pyqtSignal()
    requestHide      = pyqtSignal()
    requestQuit      = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool                # no taskbar entry
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 420)
        self._drag_pos = None
        self._build()
        self._position_top_right()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        # Header
        header = QWidget(); header.setFixedHeight(40)
        h = QHBoxLayout(header); h.setContentsMargins(12, 6, 6, 6); h.setSpacing(6)
        self.title = QLabel("J.A.R.V.I.S.")
        self.title.setStyleSheet(
            "color:#ffc23c; font-family:'Segoe UI'; font-size:11pt; "
            "font-weight:bold; letter-spacing:3px;")
        h.addWidget(self.title)
        h.addStretch()
        self.subtitle = QLabel("STANDBY")
        self.subtitle.setStyleSheet(
            "color:#be1e28; font-family:Consolas; font-size:7.5pt; letter-spacing:2px;")
        h.addWidget(self.subtitle)
        # Expand button
        self.btn_full = QPushButton("⛶")
        self.btn_full.setFixedSize(22, 22)
        self.btn_full.setToolTip("Open fullscreen Mark VII (Win+J)")
        self.btn_full.setStyleSheet(self._btn_style())
        self.btn_full.clicked.connect(lambda: self.requestImmersive.emit())
        h.addWidget(self.btn_full)
        self.btn_min = QPushButton("—")
        self.btn_min.setFixedSize(22, 22)
        self.btn_min.setToolTip("Hide (Win+J to summon)")
        self.btn_min.setStyleSheet(self._btn_style())
        self.btn_min.clicked.connect(lambda: self.requestHide.emit())
        h.addWidget(self.btn_min)
        outer.addWidget(header)

        # Arc reactor (compact)
        reactor_wrap = QWidget(); reactor_wrap.setFixedHeight(110)
        rl = QVBoxLayout(reactor_wrap); rl.setContentsMargins(0, 0, 0, 0)
        self.reactor = ArcReactor(size=100)
        rl.addWidget(self.reactor, 0, Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(reactor_wrap)

        # Agent strip
        self.agent_row = AgentRow()
        outer.addWidget(self.agent_row)

        # "Now doing" label
        self.now_label = QLabel("Awaiting wake word…")
        self.now_label.setStyleSheet(
            "color:#c8d0e0; font-family:'Segoe UI'; font-size:8.5pt; "
            "padding:6px 12px; background-color:#10141c;")
        self.now_label.setWordWrap(True)
        self.now_label.setFixedHeight(38)
        outer.addWidget(self.now_label)

        # Event stream (compact, fills rest)
        stream_wrap = QWidget()
        sl = QVBoxLayout(stream_wrap); sl.setContentsMargins(0, 4, 0, 0)
        self.stream = EventStream(max_events=12)
        sl.addWidget(self.stream)
        outer.addWidget(stream_wrap, 1)

        # Footer hint
        hint = QLabel("Win+J fullscreen · right-click for menu")
        hint.setStyleSheet("color:#5a6478; font-family:Consolas; font-size:7pt; padding:3px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setFixedHeight(20)
        outer.addWidget(hint)

    def _btn_style(self):
        return ("QPushButton {"
                "background-color:rgba(255,255,255,0.05); color:#c8d0e0;"
                "border:none; border-radius:4px; font-family:'Segoe UI'; font-size:11pt;"
                "} QPushButton:hover { background-color:rgba(255,195,60,0.2); color:#fff; }")

    def _position_top_right(self):
        scr = QApplication.primaryScreen().availableGeometry()
        self.move(scr.right() - self.width() - 16, scr.top() + 60)

    # Drag
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif e.button() == Qt.MouseButton.RightButton:
            self._show_menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self._drag_pos and (e.buttons() & Qt.MouseButton.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _):
        self._drag_pos = None

    def _show_menu(self, pos):
        m = QMenu(self)
        m.setStyleSheet("""
            QMenu { background:#10141c; color:#e6e8ee; border:1px solid #2a3140;
                    font-family:'Segoe UI'; font-size:9pt; padding:4px; }
            QMenu::item:selected { background:#1f2735; color:#ffc23c; }
        """)
        a_full = m.addAction("Open Fullscreen Mark VII")
        a_hide = m.addAction("Hide (Win+J to summon)")
        m.addSeparator()
        a_quit = m.addAction("Shutdown JARVIS")
        chosen = m.exec(pos)
        if chosen == a_full: self.requestImmersive.emit()
        elif chosen == a_hide: self.requestHide.emit()
        elif chosen == a_quit: self.requestQuit.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath(); path.addRoundedRect(rect, 12, 12)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(16, 20, 28, 235))
        grad.setColorAt(1.0, QColor(8, 10, 14, 235))
        p.fillPath(path, QBrush(grad))
        # Border + accent
        p.setPen(QPen(QColor(60, 75, 100, 180), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        # Left state accent stripe
        accent = QColor(STATE_COLOURS.get(getattr(self.reactor, 'state', 'idle'), GOLD))
        accent.setAlpha(200)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(accent))
        p.drawRoundedRect(QRectF(0, 0, 3, self.height()), 1, 1)

    def update_status(self, state):
        self.reactor.set_state(state)
        self.subtitle.setText(STATE_LABEL.get(state, state.upper()))
        self.update()


# ─── IMMERSIVE FULLSCREEN (Mark VII) ──────────────────────────────
class ImmersiveHUD(QWidget):
    requestExit = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        scr = QApplication.primaryScreen().availableGeometry()
        self.full_w, self.full_h = scr.width(), scr.height()
        self.setGeometry(scr)
        self.current_state = "idle"
        self._build()
        # ESC + Win+J + Ctrl+W all dismiss
        for key in ("Esc", "Meta+J", "Ctrl+W"):
            try:
                sc = QShortcut(QKeySequence(key), self)
                sc.activated.connect(lambda: self.requestExit.emit())
            except Exception:
                pass

    def _build(self):
        self.reactor = ArcReactor(size=320); self.reactor.setParent(self)
        rsize = 360
        self.reactor.setGeometry(
            int((self.full_w - rsize) / 2),
            int((self.full_h - rsize) / 2) - 30, rsize, rsize)

        self.title = QLabel("J.A.R.V.I.S.", self)
        self.title.setStyleSheet(
            "color:#ffc23c; font-family:'Segoe UI'; font-size:18pt; "
            "font-weight:bold; letter-spacing:8px; background:transparent;")
        self.title.setGeometry(40, 18, 400, 36)

        self.subtitle = QLabel("MARK VII  ·  STANDBY", self)
        self.subtitle.setStyleSheet(
            "color:#be1e28; font-family:Consolas; font-size:10pt; "
            "letter-spacing:4px; background:transparent;")
        self.subtitle.setGeometry(self.full_w - 350, 28, 320, 22)
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignRight)

        # CLEAR exit hint + button
        self.exit_hint = QLabel("ESC to exit  ·  Win+J to toggle", self)
        self.exit_hint.setStyleSheet(
            "color:#ffc23c; font-family:Consolas; font-size:10pt; background:transparent;")
        self.exit_hint.setGeometry(self.full_w - 350, 56, 320, 18)
        self.exit_hint.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.close_btn = QPushButton("✕  EXIT", self)
        self.close_btn.setGeometry(self.full_w - 110, 80, 90, 32)
        self.close_btn.setStyleSheet("""
            QPushButton { background-color:#be1e28; color:#fff; border:1px solid #ffc23c;
                          font-family:'Segoe UI'; font-size:9pt; font-weight:bold;
                          letter-spacing:2px; border-radius:4px; }
            QPushButton:hover { background-color:#ffc23c; color:#0c0e14; }
        """)
        self.close_btn.clicked.connect(lambda: self.requestExit.emit())

        # Event stream left
        self.stream = EventStream(max_events=22)
        self.stream.setParent(self)
        self.stream.setGeometry(40, 140, 400, self.full_h - 220)

        # Project panel right
        self.project_panel = ProjectPanel(); self.project_panel.setParent(self)
        self.project_panel.setGeometry(self.full_w - 420, 140, 380, self.full_h - 220)

        self.clock = QLabel("", self)
        self.clock.setStyleSheet(
            "color:#ebf0fa; font-family:Consolas; font-size:11pt; background:transparent;")
        self.clock.setGeometry(40, 56, 400, 22)
        t = QTimer(self); t.timeout.connect(self._update_clock); t.start(1000)
        self._update_clock()

    def _update_clock(self):
        self.clock.setText(datetime.now().strftime("%H:%M:%S  ·  %A %d %B"))

    def update_status(self, state):
        self.current_state = state
        self.reactor.set_state(state)
        self.subtitle.setText(f"MARK VII  ·  {STATE_LABEL.get(state, state.upper())}")
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(8, 10, 14, 245))
        # Horizontal lines
        p.setPen(QPen(HOT_ROD_RED, 2))
        p.drawLine(0, 118, self.full_w, 118)
        p.drawLine(0, self.full_h - 36, self.full_w, self.full_h - 36)
        # Gold corner brackets
        p.setPen(QPen(GOLD, 2))
        for cx, cy in [(20, 20), (self.full_w - 20, 20),
                       (20, self.full_h - 20), (self.full_w - 20, self.full_h - 20)]:
            sx = -1 if cx < 100 else 1
            sy = -1 if cy < 100 else 1
            p.drawLine(cx, cy, cx + 24 * sx, cy)
            p.drawLine(cx, cy, cx, cy + 24 * sy)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.requestExit.emit()
        else:
            super().keyPressEvent(e)


# ─── PROJECT PANEL ────────────────────────────────────────────────
class ProjectPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.projects = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        t = QTimer(self); t.timeout.connect(self._refresh); t.start(30000)
        self._refresh()

    def _refresh(self):
        try:
            with open(PROJECT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.projects = data.get("projects", [])[:10]
        except Exception:
            self.projects = []
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(GOLD); p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        p.drawText(8, 22, f"⚡ PROJECTS  ({len(self.projects)})")
        p.setPen(QPen(QColor(80, 90, 110, 120), 1)); p.drawLine(8, 32, w - 8, 32)
        y = 52
        for proj in self.projects:
            if y > h - 16: break
            name = proj.get("name", "?")
            stack = ",".join(proj.get("stack", [])) or "?"
            mod = proj.get("last_modified_str", "?")
            p.setPen(WHITE); p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p.drawText(8, y, name[:36])
            p.setPen(SUBTLE); p.setFont(QFont("Consolas", 8))
            p.drawText(8, y + 14, f"  {stack}  ·  {mod}")
            y += 36


# ─── CONTROLLER (manages compact + immersive + hotkey + event polling) ──
class HudController:
    def __init__(self):
        self.compact = CompactHUD()
        self.immersive = None  # lazy
        self.events_pos = 0

        self.compact.requestImmersive.connect(self.show_immersive)
        self.compact.requestHide.connect(self.hide_all)
        self.compact.requestQuit.connect(self._quit_jarvis)

        # Poll events file
        self.timer = QTimer()
        self.timer.timeout.connect(self._poll)
        self.timer.start(150)

        # Global Win+J via keyboard library, on a worker thread
        try:
            import keyboard
            keyboard.add_hotkey("windows+j", self._toggle_via_hotkey)
        except Exception as e:
            print(f"[HUD] global hotkey unavailable: {e}", flush=True)

        # Show compact on launch
        self.compact.show()

    def _toggle_via_hotkey(self):
        """Called from keyboard library's thread — marshal to Qt main thread."""
        QTimer.singleShot(0, self._toggle_state)

    def _toggle_state(self):
        if self.immersive and self.immersive.isVisible():
            self.hide_immersive()
        elif self.compact.isVisible():
            self.show_immersive()
        else:
            self.compact.show()
            self.compact.raise_()

    def show_immersive(self):
        if self.immersive is None:
            self.immersive = ImmersiveHUD()
            self.immersive.requestExit.connect(self.hide_immersive)
        self.compact.hide()
        self.immersive.show()
        self.immersive.raise_()
        self.immersive.activateWindow()
        # Sync current state
        self.immersive.update_status(self.compact.reactor.state)

    def hide_immersive(self):
        if self.immersive:
            self.immersive.hide()
        self.compact.show()
        self.compact.raise_()

    def hide_all(self):
        self.compact.hide()
        if self.immersive:
            self.immersive.hide()

    def _quit_jarvis(self):
        # Tell jarvis.py to shut down by writing a sentinel file
        try:
            with open(r"C:\Users\Dev\JARVIS\.shutdown", "w") as f:
                f.write(str(time.time()))
        except Exception:
            pass
        QApplication.quit()

    def _poll(self):
        if not os.path.exists(EVENTS_FILE):
            return
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                f.seek(self.events_pos)
                new = f.read()
                self.events_pos = f.tell()
            for line in new.splitlines():
                line = line.strip()
                if not line: continue
                try: evt = json.loads(line)
                except Exception: continue
                self._handle(evt)
        except Exception:
            pass

    def _handle(self, evt):
        kind = evt.get("kind", "")
        targets = [self.compact]
        if self.immersive and self.immersive.isVisible():
            targets.append(self.immersive)

        if kind == "status":
            state = evt.get("state", "idle")
            for t in targets:
                if hasattr(t, "update_status"):
                    t.update_status(state)
            return

        # Map event to display
        if kind == "user_said":
            text = evt.get("text", "")
            self.compact.now_label.setText(f"You: \"{text[:80]}\"")
            for t in targets:
                if hasattr(t, "stream"): t.stream.add("user_said", text)
            self.compact.reactor.pulse(0.5)
        elif kind == "speak":
            text = evt.get("text", "")
            self.compact.now_label.setText(f"JARVIS: \"{text[:80]}\"")
            for t in targets:
                if hasattr(t, "stream"): t.stream.add("speak", text)
            self.compact.reactor.pulse(0.9)
        elif kind == "tool_call":
            name = evt.get("name", "")
            args = json.dumps(evt.get("args", {}), ensure_ascii=False)[:50]
            self.compact.now_label.setText(f"→ {name}({args})")
            for t in targets:
                if hasattr(t, "stream"): t.stream.add("tool_call", f"{name}({args})")
        elif kind == "tool_result":
            for t in targets:
                if hasattr(t, "stream"):
                    t.stream.add("tool_result", f"{evt.get('name','')}: {evt.get('result','')[:80]}")
        elif kind == "shell":
            for t in targets:
                if hasattr(t, "stream"): t.stream.add("shell", evt.get("command", "")[:100])
        elif kind == "window_focus":
            for t in targets:
                if hasattr(t, "stream"): t.stream.add("window_focus", evt.get("title", "")[:80])
        elif kind == "agent_start":
            a = evt.get("agent", "")
            self.compact.agent_row.update_agent(a, "working")
            for t in targets:
                if hasattr(t, "stream"): t.stream.add("agent_start", f"{a}: {evt.get('task','')[:60]}")
        elif kind == "agent_done":
            a = evt.get("agent", "")
            self.compact.agent_row.update_agent(a, "done")
            for t in targets:
                if hasattr(t, "stream"): t.stream.add("agent_done", f"{a}: {evt.get('result','')[:80]}")
        elif kind == "predictive":
            for t in targets:
                if hasattr(t, "stream"): t.stream.add("predictive", evt.get("text", "")[:140])
        elif kind == "shutdown":
            QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ctrl = HudController()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
