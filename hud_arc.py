"""
JARVIS HUD — Mark VII cinematic interface.
Full-screen frameless overlay summoned by Win+J.
Hot rod red + gold. ARC reactor. Audio waveform. Live agent grid. Project panel.
"""

import os
import sys
import json
import math
import time
import random
from collections import deque
from datetime import datetime

from PyQt6.QtCore import (Qt, QTimer, QRectF, QPointF, QPropertyAnimation,
                          QEasingCurve, pyqtProperty, QPoint)
from PyQt6.QtGui import (QPainter, QColor, QBrush, QPen, QFont, QPainterPath,
                         QLinearGradient, QRadialGradient, QPolygonF, QFontMetrics,
                         QKeySequence, QShortcut)
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QScrollArea, QPushButton,
                             QSizePolicy)

EVENTS_FILE = r"C:\Users\Dev\JARVIS\hud_events.jsonl"
PROJECT_FILE = r"C:\Users\Dev\JARVIS\project_index.json"

# Iron Man palette
HOT_ROD_RED = QColor(190, 30, 40)
GOLD = QColor(255, 195, 60)
DEEP_BLACK = QColor(8, 10, 14)
PANEL_BG = QColor(14, 18, 26, 220)
CYAN = QColor(80, 220, 255)
WHITE = QColor(235, 240, 250)
SUBTLE = QColor(140, 150, 170)

STATE_COLOURS = {
    "idle":      QColor(120, 130, 145),
    "listening": QColor(80, 230, 120),
    "thinking":  GOLD,
    "speaking":  CYAN,
    "working":   HOT_ROD_RED,
}

STATE_LABEL = {
    "idle": "STANDBY", "listening": "LISTENING",
    "thinking": "REASONING", "speaking": "SPEAKING", "working": "EXECUTING",
}

AGENTS = ["THOR", "CAPTAIN", "HULK", "HAWKEYE", "WIDOW"]


# ─── ARC REACTOR — the centerpiece ────────────────────────────────
class ArcReactor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(280, 280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.state = "idle"
        self.phase = 0.0
        self.amplitude = 0.2
        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(30)

    def _tick(self):
        self.phase += 0.05
        # decay amplitude (so speaking pulses look natural)
        self.amplitude *= 0.96
        self.amplitude = max(self.amplitude, 0.18)
        self.update()

    def set_state(self, state):
        self.state = state
        if state == "speaking":
            self.amplitude = 1.0
        elif state == "listening":
            self.amplitude = 0.6
        elif state in ("thinking", "working"):
            self.amplitude = 0.45
        self.update()

    def pulse(self, strength=0.8):
        self.amplitude = max(self.amplitude, strength)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        base_r = min(w, h) * 0.38

        # Outer glow (color tracks state)
        glow_color = STATE_COLOURS.get(self.state, CYAN)
        for i in range(6, 0, -1):
            r = base_r + i * 14 * (1 + 0.4 * self.amplitude * math.sin(self.phase))
            alpha = int(20 + 18 * (6 - i) / 6 * self.amplitude)
            c = QColor(glow_color); c.setAlpha(alpha)
            p.setBrush(QBrush(c)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), r, r)

        # Outer ring (Iron Man triangular segments)
        segments = 9
        ring_r = base_r * 1.05
        inner_r = base_r * 0.88
        for i in range(segments):
            ang = (i / segments) * 2 * math.pi + self.phase * 0.1
            ang2 = ((i + 0.7) / segments) * 2 * math.pi + self.phase * 0.1
            poly = QPolygonF([
                QPointF(cx + ring_r * math.cos(ang), cy + ring_r * math.sin(ang)),
                QPointF(cx + ring_r * math.cos(ang2), cy + ring_r * math.sin(ang2)),
                QPointF(cx + inner_r * math.cos(ang2 - 0.05), cy + inner_r * math.sin(ang2 - 0.05)),
                QPointF(cx + inner_r * math.cos(ang + 0.05), cy + inner_r * math.sin(ang + 0.05)),
            ])
            c = QColor(glow_color); c.setAlpha(180)
            p.setBrush(QBrush(c)); p.setPen(QPen(QColor(255, 255, 255, 30), 1))
            p.drawPolygon(poly)

        # Inner ring
        p.setPen(QPen(GOLD, 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), inner_r - 4, inner_r - 4)
        p.drawEllipse(QPointF(cx, cy), inner_r - 14, inner_r - 14)

        # Core
        core_r = base_r * 0.42 + 8 * self.amplitude * abs(math.sin(self.phase * 2))
        grad = QRadialGradient(cx, cy, core_r)
        grad.setColorAt(0.0, QColor(255, 255, 255, 240))
        grad.setColorAt(0.4, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 220))
        grad.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 30))
        p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # State label
        p.setPen(GOLD)
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        label = STATE_LABEL.get(self.state, self.state.upper())
        fm = QFontMetrics(p.font())
        tw = fm.horizontalAdvance(label)
        p.drawText(int(cx - tw / 2), int(cy + base_r + 28), label)


# ─── AGENT CARD — one per Avenger ─────────────────────────────────
class AgentCard(QWidget):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.status = "idle"
        self.last_tool = ""
        self.last_result = ""
        self.pulse_level = 0.0
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        timer = QTimer(self); timer.timeout.connect(self._tick); timer.start(60)

    def _tick(self):
        self.pulse_level *= 0.9
        self.update()

    def update_status(self, status, tool="", result=""):
        self.status = status
        if tool: self.last_tool = tool
        if result: self.last_result = result
        self.pulse_level = 1.0
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height())
        # background
        bg = QColor(20, 25, 35, 200)
        path = QPainterPath(); path.addRoundedRect(rect, 8, 8)
        p.fillPath(path, QBrush(bg))
        # left status bar
        status_color = HOT_ROD_RED if self.status == "working" else (
            GOLD if self.status == "thinking" else CYAN if self.status == "done" else SUBTLE)
        status_color = QColor(status_color)
        status_color.setAlpha(int(180 + 75 * self.pulse_level))
        p.setBrush(QBrush(status_color)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, 4, self.height()), 2, 2)
        # name
        p.setPen(GOLD); p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.drawText(14, 22, self.name)
        # status text
        p.setPen(SUBTLE); p.setFont(QFont("Consolas", 8))
        status_text = self.status.upper()
        p.drawText(self.width() - 70, 22, status_text)
        # tool / result
        p.setPen(WHITE); p.setFont(QFont("Segoe UI", 9))
        line = self.last_tool[:40] if self.last_tool else "—"
        p.drawText(14, 42, f"⚙ {line}")
        if self.last_result:
            p.setPen(QColor(180, 200, 220))
            p.setFont(QFont("Segoe UI", 8))
            res = self.last_result[:60]
            p.drawText(14, 60, res)


# ─── WAVEFORM during speech ───────────────────────────────────────
class Waveform(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.active = False
        self.bars = [random.random() * 0.2 for _ in range(48)]
        timer = QTimer(self); timer.timeout.connect(self._tick); timer.start(60)

    def _tick(self):
        if self.active:
            for i in range(len(self.bars)):
                target = random.random()
                self.bars[i] = self.bars[i] * 0.6 + target * 0.4
        else:
            for i in range(len(self.bars)):
                self.bars[i] *= 0.9
        self.update()

    def set_active(self, active):
        self.active = active

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bar_w = w / len(self.bars)
        for i, v in enumerate(self.bars):
            bar_h = v * (h - 8)
            x = i * bar_w + 1
            y = (h - bar_h) / 2
            grad = QLinearGradient(0, y, 0, y + bar_h)
            grad.setColorAt(0, GOLD); grad.setColorAt(1, HOT_ROD_RED)
            p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(x, y, bar_w - 2, bar_h), 2, 2)


# ─── EVENT STREAM (left column scroll) ────────────────────────────
class EventStream(QWidget):
    def __init__(self):
        super().__init__()
        self.events = deque(maxlen=18)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def add(self, kind, text):
        self.events.append((time.time(), kind, text))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        y = h - 12
        for ts, kind, text in reversed(self.events):
            age = time.time() - ts
            alpha = max(60, int(255 - age * 4))
            kind_colors = {
                "user_said":   GOLD,
                "speak":       CYAN,
                "tool_call":   HOT_ROD_RED,
                "tool_result": QColor(80, 220, 140),
                "shell":       QColor(255, 130, 60),
                "agent_start": QColor(200, 100, 240),
                "agent_done":  QColor(120, 220, 180),
                "window_focus": SUBTLE,
            }
            kind_labels = {
                "user_said": "YOU", "speak": "JRV", "tool_call": "TOOL",
                "tool_result": " ↳ ", "shell": "SH ", "agent_start": "DEP",
                "agent_done": "RPT", "window_focus": "FOC",
            }
            c = QColor(kind_colors.get(kind, SUBTLE)); c.setAlpha(alpha)
            p.setPen(c); p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            label = kind_labels.get(kind, kind[:4].upper())
            p.drawText(8, y, label)
            tc = QColor(WHITE); tc.setAlpha(alpha)
            p.setPen(tc); p.setFont(QFont("Segoe UI", 9))
            fm = QFontMetrics(p.font())
            clipped = fm.elidedText(text, Qt.TextElideMode.ElideRight, w - 50)
            p.drawText(38, y, clipped)
            y -= 22
            if y < 24: break


# ─── PROJECT PANEL ────────────────────────────────────────────────
class ProjectPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.projects = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        timer = QTimer(self); timer.timeout.connect(self._refresh); timer.start(30000)
        self._refresh()

    def _refresh(self):
        try:
            with open(PROJECT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.projects = data.get("projects", [])[:8]
        except Exception:
            self.projects = []
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # header
        p.setPen(GOLD); p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        p.drawText(12, 22, f"⚡ PROJECTS  ({len(self.projects)} indexed)")
        # divider
        p.setPen(QPen(QColor(80, 90, 110, 120), 1))
        p.drawLine(12, 32, w - 12, 32)
        # rows
        y = 52
        for proj in self.projects:
            if y > h - 16: break
            name = proj.get("name", "?")
            stack = ",".join(proj.get("stack", [])) or "?"
            mod = proj.get("last_modified_str", "?")
            p.setPen(WHITE); p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p.drawText(12, y, name[:30])
            p.setPen(SUBTLE); p.setFont(QFont("Consolas", 8))
            p.drawText(12, y + 14, f"  {stack}  ·  {mod}")
            y += 38


# ─── PARTICLE BACKGROUND ──────────────────────────────────────────
class ParticleBg(QWidget):
    def __init__(self):
        super().__init__()
        self.particles = []
        for _ in range(40):
            self.particles.append({
                "x": random.random(), "y": random.random(),
                "vx": (random.random() - 0.5) * 0.001,
                "vy": (random.random() - 0.5) * 0.001,
                "r": random.random() * 1.5 + 0.5,
            })
        timer = QTimer(self); timer.timeout.connect(self._tick); timer.start(60)

    def _tick(self):
        for pt in self.particles:
            pt["x"] += pt["vx"]; pt["y"] += pt["vy"]
            if pt["x"] < 0 or pt["x"] > 1: pt["vx"] = -pt["vx"]
            if pt["y"] < 0 or pt["y"] > 1: pt["vy"] = -pt["vy"]
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # subtle radial vignette
        grad = QRadialGradient(w / 2, h / 2, max(w, h) / 1.2)
        grad.setColorAt(0.0, QColor(20, 22, 30, 0))
        grad.setColorAt(1.0, QColor(0, 0, 0, 180))
        p.fillRect(self.rect(), QBrush(grad))
        # particles
        for pt in self.particles:
            x = pt["x"] * w; y = pt["y"] * h
            c = QColor(255, 195, 60, 60)
            p.setBrush(QBrush(c)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, y), pt["r"], pt["r"])


# ─── MAIN HUD WINDOW ──────────────────────────────────────────────
class JarvisHUD(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S. Mark VII")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        screen = QApplication.primaryScreen().availableGeometry()
        self.full_w, self.full_h = screen.width(), screen.height()
        self.setGeometry(screen)
        self._fullscreen = True

        self._file_pos = 0
        self.current_state = "idle"

        self._build_ui()

        # Global hotkey Win+J — toggle visibility
        try:
            self.shortcut = QShortcut(QKeySequence("Meta+J"), self)
            self.shortcut.activated.connect(self.toggle_visible)
        except Exception:
            pass

        # ESC to hide
        try:
            esc = QShortcut(QKeySequence("Esc"), self)
            esc.activated.connect(self.hide)
        except Exception:
            pass

        # Poll events
        timer = QTimer(self); timer.timeout.connect(self._poll); timer.start(120)

        # Show
        self.show()

    def _build_ui(self):
        # Background layer
        self.bg = ParticleBg()
        self.bg.setParent(self)
        self.bg.setGeometry(0, 0, self.full_w, self.full_h)

        # Top header overlay
        self.header = QWidget(self)
        self.header.setGeometry(0, 0, self.full_w, 48)
        h_layout = QHBoxLayout(self.header); h_layout.setContentsMargins(28, 8, 28, 8)
        self.title_label = QLabel("J.A.R.V.I.S.")
        self.title_label.setStyleSheet(
            "color: #ffc23c; font-family: 'Segoe UI'; font-size: 16pt; "
            "font-weight: bold; letter-spacing: 6px;")
        h_layout.addWidget(self.title_label)
        h_layout.addStretch()
        self.subtitle_label = QLabel("MARK VII  ·  STANDBY")
        self.subtitle_label.setStyleSheet(
            "color: #be1e28; font-family: Consolas; font-size: 9pt; letter-spacing: 3px;")
        h_layout.addWidget(self.subtitle_label)
        h_layout.addStretch()
        self.time_label = QLabel("")
        self.time_label.setStyleSheet(
            "color: #ebf0fa; font-family: Consolas; font-size: 11pt;")
        h_layout.addWidget(self.time_label)
        # update clock
        clk = QTimer(self); clk.timeout.connect(self._update_clock); clk.start(1000)
        self._update_clock()

        # Hint footer
        self.hint = QLabel("Win+J to toggle  ·  ESC to hide  ·  drag to move (when windowed)", self)
        self.hint.setStyleSheet(
            "color: #6a7388; font-family: Consolas; font-size: 8pt; padding: 6px;")
        self.hint.setGeometry(0, self.full_h - 28, self.full_w, 28)
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Center: ARC reactor
        self.reactor = ArcReactor(self)
        rsize = 360
        self.reactor.setGeometry(
            int((self.full_w - rsize) / 2),
            int((self.full_h - rsize) / 2) - 20,
            rsize, rsize,
        )

        # Left column: event stream
        self.event_stream = EventStream()
        self.event_stream.setParent(self)
        self.event_stream.setGeometry(28, 80, 360, self.full_h - 160)

        # Right column: agent grid + project panel
        right_w = 380
        right_x = self.full_w - right_w - 28

        agent_panel = QWidget(self)
        agent_panel.setGeometry(right_x, 80, right_w, 5 * 80 + 16)
        agent_layout = QVBoxLayout(agent_panel)
        agent_layout.setContentsMargins(0, 0, 0, 0); agent_layout.setSpacing(6)
        self.agent_cards = {}
        for a in AGENTS:
            card = AgentCard(a)
            self.agent_cards[a] = card
            agent_layout.addWidget(card)

        # Project panel below agents
        self.project_panel = ProjectPanel()
        self.project_panel.setParent(self)
        proj_y = 80 + (5 * 80 + 16) + 12
        self.project_panel.setGeometry(right_x, proj_y, right_w,
                                       self.full_h - proj_y - 60)

        # Bottom waveform
        self.waveform = Waveform()
        self.waveform.setParent(self)
        wf_w = 600
        self.waveform.setGeometry(
            int((self.full_w - wf_w) / 2), self.full_h - 110, wf_w, 70)

    def _update_clock(self):
        self.time_label.setText(datetime.now().strftime("%H:%M:%S  ·  %a %d %b"))

    def toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Dark background
        p.fillRect(self.rect(), QColor(8, 10, 14, 230))
        # Red horizontal lines top/bottom
        p.setPen(QPen(HOT_ROD_RED, 2))
        p.drawLine(0, 56, self.full_w, 56)
        p.drawLine(0, self.full_h - 36, self.full_w, self.full_h - 36)
        # Gold corner brackets
        p.setPen(QPen(GOLD, 2))
        for cx, cy in [(20, 20), (self.full_w - 20, 20),
                       (20, self.full_h - 20), (self.full_w - 20, self.full_h - 20)]:
            sx = -1 if cx < 100 else 1
            sy = -1 if cy < 100 else 1
            p.drawLine(cx, cy, cx + 24 * sx, cy)
            p.drawLine(cx, cy, cx, cy + 24 * sy)

    def _poll(self):
        if not os.path.exists(EVENTS_FILE):
            return
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                f.seek(self._file_pos)
                new = f.read()
                self._file_pos = f.tell()
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
        if kind == "status":
            state = evt.get("state", "idle")
            self.current_state = state
            self.reactor.set_state(state)
            self.subtitle_label.setText(f"MARK VII  ·  {STATE_LABEL.get(state, state.upper())}")
            self.waveform.set_active(state == "speaking")
            return
        if kind == "user_said":
            self.event_stream.add("user_said", evt.get("text", ""))
            self.reactor.pulse(0.5)
            return
        if kind == "speak":
            self.event_stream.add("speak", evt.get("text", ""))
            self.reactor.pulse(0.9)
            return
        if kind == "tool_call":
            name = evt.get("name", "")
            args = json.dumps(evt.get("args", {}), ensure_ascii=False)[:60]
            self.event_stream.add("tool_call", f"{name}({args})")
            return
        if kind == "tool_result":
            self.event_stream.add("tool_result", f"{evt.get('name','')} → {evt.get('result','')[:80]}")
            return
        if kind == "shell":
            self.event_stream.add("shell", evt.get("command", "")[:120])
            return
        if kind == "window_focus":
            self.event_stream.add("window_focus", evt.get("title", "")[:80])
            return
        if kind == "agent_start":
            a = evt.get("agent", "")
            if a in self.agent_cards:
                self.agent_cards[a].update_status("working", tool=evt.get("task", "")[:50])
            self.event_stream.add("agent_start", f"{a}: {evt.get('task','')[:60]}")
            return
        if kind == "agent_tool":
            a = evt.get("agent", "")
            if a in self.agent_cards:
                self.agent_cards[a].update_status("working", tool=evt.get("tool", ""))
            return
        if kind == "agent_done":
            a = evt.get("agent", "")
            if a in self.agent_cards:
                self.agent_cards[a].update_status("done", result=evt.get("result", "")[:80])
            self.event_stream.add("agent_done", f"{a}: {evt.get('result','')[:80]}")
            return
        if kind == "crew_dispatch":
            self.event_stream.add("agent_start", f"CREW: {evt.get('task','')[:80]}")
            return
        if kind == "crew_report":
            self.event_stream.add("agent_done", f"REPORT: {evt.get('report','')[:80]}")
            return

    def closeEvent(self, e):
        # Don't actually close — hide instead so global hotkey can bring it back
        e.ignore()
        self.hide()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    hud = JarvisHUD()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
