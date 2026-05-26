"""
JARVIS HUD — Stark Industries Mark VIII
Cyan circular-gauge aesthetic from the Iron Man films.
Two modes:
  COMPACT  — small floating widget, top-right, draggable, non-blocking.
  IMMERSIVE — fullscreen Stark dashboard, multiple circular gauges,
              calendar strip, weather forecast, audio waveform,
              system stats, music controls, STARK INDUSTRIES branding.
Global hotkey: Win+J cycles hidden -> compact -> immersive -> hidden.
"""

import os
import sys
import json
import math
import time
import random
import threading
from collections import deque
from datetime import datetime, timedelta

from PyQt6.QtCore import (Qt, QTimer, QRectF, QPointF, pyqtSignal,
                          pyqtSlot, QPoint, QEvent)
from PyQt6.QtGui import (QPainter, QColor, QBrush, QPen, QFont, QPainterPath,
                         QLinearGradient, QRadialGradient, QPolygonF,
                         QFontMetrics, QKeySequence, QShortcut, QConicalGradient)
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSizePolicy, QMenu)

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False

EVENTS_FILE  = r"C:\Users\Dev\JARVIS\hud_events.jsonl"
PROJECT_FILE = r"C:\Users\Dev\JARVIS\project_index.json"
TASKS_FILE   = r"C:\Users\Dev\JARVIS\tasks.json"

# ═══════════════════════════════════════════════════════════════
# STARK INDUSTRIES PALETTE — cyan + dark
# ═══════════════════════════════════════════════════════════════
CYAN_BRIGHT  = QColor(0, 220, 255)
CYAN         = QColor(0, 180, 230)
CYAN_DARK    = QColor(0, 100, 140)
CYAN_FAINT   = QColor(0, 180, 230, 70)
DEEP_BLACK   = QColor(4, 8, 14)
PANEL_BG     = QColor(8, 14, 22, 230)
TEXT_WHITE   = QColor(225, 240, 252)
TEXT_DIM     = QColor(110, 150, 180)
AMBER        = QColor(255, 165, 50)
STATE_RED    = QColor(255, 80, 80)
STATE_GREEN  = QColor(80, 230, 130)

STATE_COLOURS = {
    "idle":      CYAN,
    "listening": STATE_GREEN,
    "thinking":  AMBER,
    "speaking":  CYAN_BRIGHT,
    "working":   QColor(220, 80, 220),
}
STATE_LABEL = {
    "idle": "STANDBY", "listening": "LISTENING",
    "thinking": "REASONING", "speaking": "SPEAKING", "working": "EXECUTING",
}
AGENTS = ["THOR", "CAPTAIN", "HULK", "HAWKEYE", "WIDOW", "BUILDER"]


# ═══════════════════════════════════════════════════════════════
# CIRCULAR GAUGE — the heart of the Stark aesthetic
# ═══════════════════════════════════════════════════════════════
class CircularGauge(QWidget):
    """One concentric-ring circular widget with text inside."""
    def __init__(self, size=120, title="", value_fn=None, unit="",
                 max_value=100.0, accent=CYAN):
        super().__init__()
        self.setFixedSize(size, size)
        self.title = title
        self.value_fn = value_fn   # callable returning current value
        self.unit = unit
        self.max_value = max_value
        self.accent = accent
        self.value = 0.0
        self.phase = 0.0
        timer = QTimer(self); timer.timeout.connect(self._tick); timer.start(500)

    def _tick(self):
        if self.value_fn:
            try:
                v = self.value_fn()
                if v is not None: self.value = float(v)
            except Exception:
                pass
        self.phase += 0.02
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r_outer = min(w, h) / 2 - 6

        # Outer ring (faint full circle)
        p.setPen(QPen(CYAN_DARK, 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r_outer, r_outer)

        # Animated arc — value fill
        frac = min(1.0, max(0.0, self.value / max(self.max_value, 1)))
        pen = QPen(self.accent, 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(
            int(cx - r_outer + 4), int(cy - r_outer + 4),
            int((r_outer - 4) * 2), int((r_outer - 4) * 2),
            int(90 * 16),               # start at top
            int(-frac * 360 * 16),      # clockwise
        )

        # Inner ring
        inner_r = r_outer - 12
        p.setPen(QPen(CYAN_FAINT, 1))
        p.drawEllipse(QPointF(cx, cy), inner_r, inner_r)

        # Tick marks around the gauge
        p.setPen(QPen(CYAN_DARK, 1))
        for i in range(60):
            a = i / 60 * 2 * math.pi - math.pi / 2
            r1 = r_outer - 6
            r2 = r_outer - 2 if i % 5 == 0 else r_outer - 4
            p.drawLine(
                QPointF(cx + r1 * math.cos(a), cy + r1 * math.sin(a)),
                QPointF(cx + r2 * math.cos(a), cy + r2 * math.sin(a)),
            )

        # Value text center
        p.setPen(self.accent)
        p.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        if self.unit == "%":
            txt = f"{int(self.value)}%"
        elif self.unit:
            txt = f"{int(self.value)}{self.unit}"
        else:
            txt = f"{int(self.value)}"
        fm = QFontMetrics(p.font())
        tw = fm.horizontalAdvance(txt)
        p.drawText(int(cx - tw / 2), int(cy + 6), txt)

        # Title above value
        if self.title:
            p.setPen(TEXT_DIM)
            p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            fm = QFontMetrics(p.font())
            tw = fm.horizontalAdvance(self.title)
            p.drawText(int(cx - tw / 2), int(cy - 6), self.title)


# ═══════════════════════════════════════════════════════════════
# DATE / TIME / DAY DISPLAY (left big circle)
# ═══════════════════════════════════════════════════════════════
class DateCircle(QWidget):
    def __init__(self, size=180):
        super().__init__()
        self.setFixedSize(size, size)
        timer = QTimer(self); timer.timeout.connect(self.update); timer.start(1000)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 8

        # Outer ring
        p.setPen(QPen(CYAN, 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.setPen(QPen(CYAN_FAINT, 1))
        p.drawEllipse(QPointF(cx, cy), r - 8, r - 8)

        # Tick marks
        p.setPen(QPen(CYAN_DARK, 1))
        for i in range(30):
            a = i / 30 * 2 * math.pi - math.pi / 2
            r1 = r - 2; r2 = r - 6 if i % 5 == 0 else r - 4
            p.drawLine(QPointF(cx + r1 * math.cos(a), cy + r1 * math.sin(a)),
                       QPointF(cx + r2 * math.cos(a), cy + r2 * math.sin(a)))

        now = datetime.now()
        # Month
        p.setPen(TEXT_DIM); p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        month = now.strftime("%B").upper()
        fm = QFontMetrics(p.font())
        p.drawText(int(cx - fm.horizontalAdvance(month) / 2), int(cy - 24), month)
        # Day number — big
        p.setPen(CYAN_BRIGHT)
        p.setFont(QFont("Consolas", 36, QFont.Weight.Bold))
        day = now.strftime("%d")
        fm = QFontMetrics(p.font())
        p.drawText(int(cx - fm.horizontalAdvance(day) / 2), int(cy + 18), day)
        # Weekday
        p.setPen(TEXT_DIM); p.setFont(QFont("Consolas", 9))
        wd = now.strftime("%A").upper()
        fm = QFontMetrics(p.font())
        p.drawText(int(cx - fm.horizontalAdvance(wd) / 2), int(cy + 36), wd)


class TimeCircle(QWidget):
    def __init__(self, size=180):
        super().__init__()
        self.setFixedSize(size, size)
        timer = QTimer(self); timer.timeout.connect(self.update); timer.start(1000)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 8

        # Outer ring
        p.setPen(QPen(CYAN, 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.setPen(QPen(CYAN_FAINT, 1))
        p.drawEllipse(QPointF(cx, cy), r - 8, r - 8)

        # 60-tick ring
        p.setPen(QPen(CYAN_DARK, 1))
        for i in range(60):
            a = i / 60 * 2 * math.pi - math.pi / 2
            r1 = r - 2; r2 = r - 8 if i % 5 == 0 else r - 4
            p.drawLine(QPointF(cx + r1 * math.cos(a), cy + r1 * math.sin(a)),
                       QPointF(cx + r2 * math.cos(a), cy + r2 * math.sin(a)))

        # Seconds arc (animated)
        now = datetime.now()
        sec_frac = (now.second + now.microsecond / 1e6) / 60.0
        pen = QPen(CYAN_BRIGHT, 3); pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(int(cx - r + 4), int(cy - r + 4),
                  int((r - 4) * 2), int((r - 4) * 2),
                  int(90 * 16), int(-sec_frac * 360 * 16))

        # Time text
        p.setPen(CYAN_BRIGHT)
        p.setFont(QFont("Consolas", 24, QFont.Weight.Bold))
        t = now.strftime("%H:%M")
        fm = QFontMetrics(p.font())
        p.drawText(int(cx - fm.horizontalAdvance(t) / 2), int(cy + 4), t)
        # Seconds small
        p.setPen(TEXT_DIM)
        p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        secs = now.strftime("%S")
        fm = QFontMetrics(p.font())
        p.drawText(int(cx - fm.horizontalAdvance(secs) / 2), int(cy + 24), secs)


# ═══════════════════════════════════════════════════════════════
# ARC REACTOR — center piece
# ═══════════════════════════════════════════════════════════════
class ArcReactor(QWidget):
    def __init__(self, size=320):
        super().__init__()
        self.setFixedSize(size, size)
        self.state = "idle"
        self.phase = 0.0
        self.amplitude = 0.3
        t = QTimer(self); t.timeout.connect(self._tick); t.start(40)

    def _tick(self):
        self.phase += 0.05
        self.amplitude = max(self.amplitude * 0.96, 0.25)
        self.update()

    def set_state(self, state):
        self.state = state
        if state == "speaking": self.amplitude = 1.0
        elif state == "listening": self.amplitude = 0.7
        elif state in ("thinking", "working"): self.amplitude = 0.5
        self.update()

    def pulse(self, s=0.8):
        self.amplitude = max(self.amplitude, s)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        base_r = min(w, h) * 0.34
        glow = STATE_COLOURS.get(self.state, CYAN_BRIGHT)

        # Multi-layer glow
        for i in range(7, 0, -1):
            r = base_r + i * 10 * (1 + 0.4 * self.amplitude * math.sin(self.phase))
            c = QColor(glow); c.setAlpha(int(15 + 18 * (7 - i) / 7 * self.amplitude))
            p.setBrush(QBrush(c)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), r, r)

        # Conic gradient ring (rotating energy)
        cg = QConicalGradient(QPointF(cx, cy), -self.phase * 50)
        cg.setColorAt(0.0, glow)
        cg.setColorAt(0.3, CYAN_BRIGHT)
        cg.setColorAt(0.5, glow)
        cg.setColorAt(0.7, CYAN_BRIGHT)
        cg.setColorAt(1.0, glow)
        pen = QPen(QBrush(cg), 8); pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), base_r * 1.05, base_r * 1.05)

        # Segmented inner ring
        segs = 12
        ring_r = base_r * 0.88
        inner_r = base_r * 0.72
        for i in range(segs):
            a1 = (i / segs) * 2 * math.pi + self.phase * 0.15
            a2 = ((i + 0.75) / segs) * 2 * math.pi + self.phase * 0.15
            poly = QPolygonF([
                QPointF(cx + ring_r * math.cos(a1), cy + ring_r * math.sin(a1)),
                QPointF(cx + ring_r * math.cos(a2), cy + ring_r * math.sin(a2)),
                QPointF(cx + inner_r * math.cos(a2 - 0.05), cy + inner_r * math.sin(a2 - 0.05)),
                QPointF(cx + inner_r * math.cos(a1 + 0.05), cy + inner_r * math.sin(a1 + 0.05)),
            ])
            c = QColor(glow); c.setAlpha(180)
            p.setBrush(QBrush(c)); p.setPen(QPen(QColor(255, 255, 255, 30), 1))
            p.drawPolygon(poly)

        # Two faint inner rings
        p.setPen(QPen(CYAN_FAINT, 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), inner_r - 6, inner_r - 6)
        p.drawEllipse(QPointF(cx, cy), inner_r - 20, inner_r - 20)

        # Core (the reactor core)
        cr = base_r * 0.36 + 6 * self.amplitude * abs(math.sin(self.phase * 2))
        grad = QRadialGradient(cx, cy, cr)
        grad.setColorAt(0.0, QColor(255, 255, 255, 245))
        grad.setColorAt(0.35, QColor(glow.red(), glow.green(), glow.blue(), 220))
        grad.setColorAt(1.0, QColor(glow.red(), glow.green(), glow.blue(), 20))
        p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), cr, cr)

        # State label below
        p.setPen(CYAN_BRIGHT)
        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        label = STATE_LABEL.get(self.state, self.state.upper())
        fm = QFontMetrics(p.font())
        p.drawText(int(cx - fm.horizontalAdvance(label) / 2),
                   int(cy + base_r + 28), label)


# ═══════════════════════════════════════════════════════════════
# CALENDAR STRIP (top — shows whole month with current day highlighted)
# ═══════════════════════════════════════════════════════════════
class CalendarStrip(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(40)
        timer = QTimer(self); timer.timeout.connect(self.update); timer.start(60000)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        now = datetime.now()
        # Days in current month
        if now.month == 12:
            next_m = datetime(now.year + 1, 1, 1)
        else:
            next_m = datetime(now.year, now.month + 1, 1)
        last_day = (next_m - timedelta(days=1)).day
        cell_w = (w - 40) / last_day
        p.setFont(QFont("Consolas", 9))
        for d in range(1, last_day + 1):
            x = 20 + (d - 0.5) * cell_w
            if d == now.day:
                # Highlight current day
                p.setBrush(QBrush(CYAN_BRIGHT)); p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(QRectF(x - cell_w/2 + 2, 4, cell_w - 4, h - 12),
                                  3, 3)
                p.setPen(DEEP_BLACK); p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            else:
                p.setPen(TEXT_DIM); p.setFont(QFont("Consolas", 9))
            fm = QFontMetrics(p.font())
            txt = f"{d:02d}"
            p.drawText(int(x - fm.horizontalAdvance(txt) / 2),
                       int(h / 2 + 4), txt)
        # Bottom line
        p.setPen(QPen(CYAN_DARK, 1))
        p.drawLine(20, h - 6, w - 20, h - 6)


# ═══════════════════════════════════════════════════════════════
# WEATHER FORECAST (right column — 7 day strip)
# ═══════════════════════════════════════════════════════════════
class WeatherPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.forecast = []  # list of (day_short, temp_c, condition)
        timer = QTimer(self); timer.timeout.connect(self._refresh); timer.start(600_000)
        self._refresh()

    def _refresh(self):
        def fetch():
            try:
                import urllib.request, urllib.parse
                url = "https://wttr.in/Greater+Noida?format=j1"
                req = urllib.request.Request(url, headers={"User-Agent": "JARVIS"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    data = json.loads(r.read().decode())
                weather = data.get("weather", [])[:5]
                out = []
                for day in weather:
                    date = day.get("date", "")
                    try:
                        dt = datetime.strptime(date, "%Y-%m-%d")
                        dlabel = dt.strftime("%a").upper()
                    except Exception:
                        dlabel = "?"
                    avg = day.get("avgtempC", "?")
                    cond = day.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", "")
                    out.append((dlabel, avg, cond[:14]))
                self.forecast = out
                self.update()
            except Exception:
                pass
        threading.Thread(target=fetch, daemon=True).start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # Header
        p.setPen(CYAN); p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        p.drawText(8, 18, "▣ FORECAST  GREATER NOIDA")
        p.setPen(QPen(CYAN_DARK, 1)); p.drawLine(8, 26, w - 8, 26)
        y = 50
        for label, temp, cond in self.forecast:
            if y > h - 16: break
            p.setPen(TEXT_WHITE); p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            p.drawText(12, y, label)
            p.setPen(CYAN_BRIGHT); p.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
            p.drawText(60, y + 2, f"{temp}°")
            p.setPen(TEXT_DIM); p.setFont(QFont("Consolas", 8))
            p.drawText(110, y, cond)
            y += 30


# ═══════════════════════════════════════════════════════════════
# AUDIO WAVEFORM — speaking visualization
# ═══════════════════════════════════════════════════════════════
class Waveform(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(60)
        self.bars = [random.random() * 0.15 for _ in range(64)]
        self.active = False
        t = QTimer(self); t.timeout.connect(self._tick); t.start(50)

    def _tick(self):
        if self.active:
            for i in range(len(self.bars)):
                self.bars[i] = self.bars[i] * 0.55 + random.random() * 0.45
        else:
            for i in range(len(self.bars)):
                self.bars[i] *= 0.9
        self.update()

    def set_active(self, a): self.active = a

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
            grad.setColorAt(0, CYAN_BRIGHT); grad.setColorAt(1, CYAN_DARK)
            p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(x, y, bar_w - 2, bar_h), 1, 1)


# ═══════════════════════════════════════════════════════════════
# EVENT STREAM
# ═══════════════════════════════════════════════════════════════
class EventStream(QWidget):
    def __init__(self, max_events=20):
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
        # Header
        p.setPen(CYAN); p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        p.drawText(8, 18, "▣ ACTIVITY STREAM")
        p.setPen(QPen(CYAN_DARK, 1)); p.drawLine(8, 26, w - 8, 26)
        y = h - 10
        for ts, kind, text in reversed(self.events):
            age = time.time() - ts
            alpha = max(70, int(255 - age * 3))
            kc = {
                "user_said": AMBER, "speak": CYAN_BRIGHT, "tool_call": CYAN,
                "tool_result": STATE_GREEN, "shell": QColor(255, 130, 60),
                "agent_start": QColor(200, 100, 240), "agent_done": STATE_GREEN,
                "window_focus": TEXT_DIM, "predictive": AMBER,
            }
            kl = {
                "user_said": "YOU", "speak": "JRV", "tool_call": "TL",
                "tool_result": " >", "shell": "SH", "agent_start": ">",
                "agent_done": "<", "window_focus": "FW", "predictive": "AMB",
            }
            c = QColor(kc.get(kind, TEXT_DIM)); c.setAlpha(alpha)
            p.setPen(c); p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            p.drawText(8, y, kl.get(kind, kind[:3].upper()))
            tc = QColor(TEXT_WHITE); tc.setAlpha(alpha)
            p.setPen(tc); p.setFont(QFont("Consolas", 9))
            fm = QFontMetrics(p.font())
            clip = fm.elidedText(text, Qt.TextElideMode.ElideRight, w - 50)
            p.drawText(36, y, clip)
            y -= 18
            if y < 36: break


# ═══════════════════════════════════════════════════════════════
# PROJECT PANEL
# ═══════════════════════════════════════════════════════════════
class ProjectPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.projects = []
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
        p.setPen(CYAN); p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        p.drawText(8, 18, f"▣ PROJECTS  ({len(self.projects)})")
        p.setPen(QPen(CYAN_DARK, 1)); p.drawLine(8, 26, w - 8, 26)
        y = 50
        for proj in self.projects:
            if y > h - 16: break
            name = proj.get("name", "?")
            stack = ",".join(proj.get("stack", [])) or "?"
            mod = proj.get("last_modified_str", "?")
            p.setPen(TEXT_WHITE); p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p.drawText(8, y, name[:32])
            p.setPen(TEXT_DIM); p.setFont(QFont("Consolas", 8))
            p.drawText(8, y + 14, f"  {stack}  ·  {mod}")
            y += 36


# ═══════════════════════════════════════════════════════════════
# TASK PANEL
# ═══════════════════════════════════════════════════════════════
class TaskPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.tasks = []
        timer = QTimer(self); timer.timeout.connect(self._refresh); timer.start(15000)
        self._refresh()

    def _refresh(self):
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.tasks = data.get("pending", [])[:6]
        except Exception:
            self.tasks = []
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(CYAN); p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        p.drawText(8, 18, f"▣ TASKS  ({len(self.tasks)})")
        p.setPen(QPen(CYAN_DARK, 1)); p.drawLine(8, 26, w - 8, 26)
        y = 50
        for task in self.tasks:
            if y > h - 16: break
            txt = task.get("text", "?")
            pri = task.get("priority", "med")
            pri_color = STATE_RED if pri == "high" else AMBER if pri == "medium" else TEXT_DIM
            p.setPen(pri_color); p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            p.drawText(8, y, f"[{pri[0].upper()}]")
            p.setPen(TEXT_WHITE); p.setFont(QFont("Segoe UI", 9))
            fm = QFontMetrics(p.font())
            clip = fm.elidedText(txt, Qt.TextElideMode.ElideRight, w - 50)
            p.drawText(36, y, clip)
            y += 22


# ═══════════════════════════════════════════════════════════════
# AGENT STRIP
# ═══════════════════════════════════════════════════════════════
class AgentRow(QWidget):
    def __init__(self):
        super().__init__()
        self.statuses = {a: "idle" for a in AGENTS}
        self.setFixedHeight(38)

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
            c = STATE_RED if stat == "working" else AMBER if stat == "thinking" \
                else STATE_GREEN if stat == "done" else TEXT_DIM
            p.setBrush(QBrush(c)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, 10), 5, 5)
            p.setPen(CYAN); p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            fm = QFontMetrics(p.font())
            tw = fm.horizontalAdvance(a)
            p.drawText(int(x - tw / 2), 30, a)


# ═══════════════════════════════════════════════════════════════
# CPU / RAM / DISK GAUGES (data source)
# ═══════════════════════════════════════════════════════════════
def _cpu_value():
    if not PSUTIL_OK: return 0
    return psutil.cpu_percent(interval=None)

def _ram_value():
    if not PSUTIL_OK: return 0
    return psutil.virtual_memory().percent

def _disk_value():
    if not PSUTIL_OK: return 0
    try:
        return psutil.disk_usage("C:\\").percent
    except Exception:
        return 0

def _battery_value():
    if not PSUTIL_OK: return 0
    try:
        b = psutil.sensors_battery()
        return b.percent if b else 0
    except Exception:
        return 0


# ═══════════════════════════════════════════════════════════════
# COMPACT MODE — small floating top-right
# ═══════════════════════════════════════════════════════════════
class CompactHUD(QWidget):
    requestImmersive = pyqtSignal()
    requestHide      = pyqtSignal()
    requestQuit      = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(340, 460)
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
        self.title.setStyleSheet("color:#00dcff; font-family:'Segoe UI'; font-size:11pt; font-weight:bold; letter-spacing:3px;")
        h.addWidget(self.title)
        h.addStretch()
        self.subtitle = QLabel("STANDBY")
        self.subtitle.setStyleSheet("color:#00b4e6; font-family:Consolas; font-size:7.5pt; letter-spacing:2px;")
        h.addWidget(self.subtitle)
        self.btn_full = QPushButton("⛶")
        self.btn_full.setFixedSize(22, 22)
        self.btn_full.setStyleSheet(self._btn_style())
        self.btn_full.setToolTip("Open fullscreen dashboard (Win+J)")
        self.btn_full.clicked.connect(lambda: self.requestImmersive.emit())
        h.addWidget(self.btn_full)
        self.btn_min = QPushButton("—")
        self.btn_min.setFixedSize(22, 22)
        self.btn_min.setStyleSheet(self._btn_style())
        self.btn_min.setToolTip("Hide (Win+J to summon)")
        self.btn_min.clicked.connect(lambda: self.requestHide.emit())
        h.addWidget(self.btn_min)
        outer.addWidget(header)

        # Arc reactor center
        rwrap = QWidget(); rwrap.setFixedHeight(130)
        rl = QVBoxLayout(rwrap); rl.setContentsMargins(0, 0, 0, 0)
        self.reactor = ArcReactor(size=120)
        rl.addWidget(self.reactor, 0, Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(rwrap)

        # Mini gauges row
        gauges = QWidget(); gauges.setFixedHeight(70)
        gl = QHBoxLayout(gauges); gl.setContentsMargins(8, 0, 8, 0); gl.setSpacing(4)
        self.g_cpu  = CircularGauge(60, "CPU", _cpu_value, "%", 100, CYAN)
        self.g_ram  = CircularGauge(60, "RAM", _ram_value, "%", 100, CYAN_BRIGHT)
        self.g_disk = CircularGauge(60, "DSK", _disk_value, "%", 100, AMBER)
        self.g_batt = CircularGauge(60, "BAT", _battery_value, "%", 100, STATE_GREEN)
        for g in (self.g_cpu, self.g_ram, self.g_disk, self.g_batt):
            gl.addWidget(g)
        outer.addWidget(gauges)

        # Agent strip
        self.agent_row = AgentRow()
        outer.addWidget(self.agent_row)

        # Now-doing label
        self.now_label = QLabel("Awaiting wake word…")
        self.now_label.setStyleSheet("color:#c8d0e0; font-family:'Segoe UI'; font-size:8.5pt; padding:6px 12px; background-color:#080e16;")
        self.now_label.setWordWrap(True)
        self.now_label.setFixedHeight(40)
        outer.addWidget(self.now_label)

        # Stream
        self.stream = EventStream(max_events=10)
        outer.addWidget(self.stream, 1)

        # Footer
        hint = QLabel("Win+J fullscreen · right-click for menu")
        hint.setStyleSheet("color:#6e96b4; font-family:Consolas; font-size:7pt; padding:3px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setFixedHeight(20)
        outer.addWidget(hint)

    def _btn_style(self):
        return ("QPushButton {background-color:rgba(0,180,230,0.1); color:#c8d0e0;"
                "border:none; border-radius:4px; font-family:'Segoe UI'; font-size:11pt;}"
                "QPushButton:hover {background-color:rgba(0,220,255,0.25); color:#fff;}")

    def _position_top_right(self):
        scr = QApplication.primaryScreen().availableGeometry()
        self.move(scr.right() - self.width() - 16, scr.top() + 60)

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
            QMenu { background:#080e16; color:#e1f0fc; border:1px solid #0064; font-family:'Segoe UI'; font-size:9pt; padding:4px; }
            QMenu::item:selected { background:#0a1828; color:#00dcff; }
        """)
        a_full = m.addAction("Open Fullscreen Dashboard")
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
        grad.setColorAt(0.0, QColor(8, 14, 22, 240))
        grad.setColorAt(1.0, QColor(4, 8, 14, 240))
        p.fillPath(path, QBrush(grad))
        p.setPen(QPen(CYAN_FAINT, 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        # Cyan left accent stripe
        accent = QColor(STATE_COLOURS.get(getattr(self.reactor, 'state', 'idle'), CYAN))
        accent.setAlpha(220)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(accent))
        p.drawRoundedRect(QRectF(0, 0, 3, self.height()), 1, 1)

    def update_status(self, state):
        self.reactor.set_state(state)
        self.subtitle.setText(STATE_LABEL.get(state, state.upper()))
        self.update()


# ═══════════════════════════════════════════════════════════════
# IMMERSIVE MODE — Stark Industries fullscreen
# ═══════════════════════════════════════════════════════════════
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
        for key in ("Esc", "Meta+J", "Ctrl+W"):
            try:
                sc = QShortcut(QKeySequence(key), self)
                sc.activated.connect(lambda: self.requestExit.emit())
            except Exception:
                pass

    def _build(self):
        # Calendar strip top
        self.cal = CalendarStrip(); self.cal.setParent(self)
        self.cal.setGeometry(40, 16, self.full_w - 80, 40)

        # Top-left title
        self.title = QLabel("J.A.R.V.I.S.", self)
        self.title.setStyleSheet("color:#00dcff; font-family:'Segoe UI'; font-size:20pt; font-weight:bold; letter-spacing:8px; background:transparent;")
        self.title.setGeometry(40, 60, 400, 36)

        # Mark / state subtitle (top-right)
        self.subtitle = QLabel("MARK VIII  ·  STANDBY", self)
        self.subtitle.setStyleSheet("color:#00b4e6; font-family:Consolas; font-size:10pt; letter-spacing:4px; background:transparent;")
        self.subtitle.setGeometry(self.full_w - 380, 70, 320, 22)
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Exit hint + button (top-right corner)
        self.exit_hint = QLabel("ESC · Win+J to dismiss", self)
        self.exit_hint.setStyleSheet("color:#ffa532; font-family:Consolas; font-size:9pt; background:transparent;")
        self.exit_hint.setGeometry(self.full_w - 380, 96, 320, 18)
        self.exit_hint.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.close_btn = QPushButton("✕  EXIT", self)
        self.close_btn.setGeometry(self.full_w - 110, 120, 90, 32)
        self.close_btn.setStyleSheet("""
            QPushButton { background-color:#00dcff; color:#040810; border:1px solid #fff; font-family:'Segoe UI'; font-size:9pt; font-weight:bold; letter-spacing:2px; border-radius:4px; }
            QPushButton:hover { background-color:#fff; color:#040810; }
        """)
        self.close_btn.clicked.connect(lambda: self.requestExit.emit())

        # Center ARC reactor (huge)
        self.reactor = ArcReactor(size=380); self.reactor.setParent(self)
        rsize = 380
        self.reactor.setGeometry(
            int((self.full_w - rsize) / 2),
            int((self.full_h - rsize) / 2) - 40, rsize, rsize)

        # Date and time big circles (flanking the reactor)
        self.date_circle = DateCircle(180); self.date_circle.setParent(self)
        self.date_circle.move(
            int((self.full_w - rsize) / 2) - 220,
            int((self.full_h - 180) / 2) - 40)
        self.time_circle = TimeCircle(180); self.time_circle.setParent(self)
        self.time_circle.move(
            int((self.full_w + rsize) / 2) + 40,
            int((self.full_h - 180) / 2) - 40)

        # System gauges row (left under date circle)
        gauge_y = int((self.full_h - 180) / 2) + 160
        self.g_cpu  = CircularGauge(110, "CPU",  _cpu_value, "%", 100, CYAN)
        self.g_ram  = CircularGauge(110, "RAM",  _ram_value, "%", 100, CYAN_BRIGHT)
        self.g_disk = CircularGauge(110, "DISK", _disk_value, "%", 100, AMBER)
        self.g_batt = CircularGauge(110, "BATT", _battery_value, "%", 100, STATE_GREEN)
        for i, g in enumerate((self.g_cpu, self.g_ram, self.g_disk, self.g_batt)):
            g.setParent(self)
            g.move(40 + i * 120, gauge_y)

        # Left column — event stream
        self.stream = EventStream(max_events=22)
        self.stream.setParent(self)
        self.stream.setGeometry(40, 160, 380, gauge_y - 180)

        # Right column — weather + projects + tasks
        right_w = 380; right_x = self.full_w - right_w - 40
        self.weather = WeatherPanel(); self.weather.setParent(self)
        self.weather.setGeometry(right_x, 160, right_w, 220)
        self.projects = ProjectPanel(); self.projects.setParent(self)
        self.projects.setGeometry(right_x, 400, right_w, 320)
        self.tasks = TaskPanel(); self.tasks.setParent(self)
        self.tasks.setGeometry(right_x, 740, right_w, self.full_h - 740 - 100)

        # Agent strip bottom-center
        self.agent_row = AgentRow(); self.agent_row.setParent(self)
        self.agent_row.setGeometry(int((self.full_w - 500) / 2),
                                    self.full_h - 130, 500, 38)

        # Waveform bottom
        self.waveform = Waveform(); self.waveform.setParent(self)
        wf_w = 700
        self.waveform.setGeometry(int((self.full_w - wf_w) / 2),
                                   self.full_h - 90, wf_w, 60)

        # Footer
        self.footer = QLabel("STARK INDUSTRIES  ·  J.A.R.V.I.S. PERSONAL ASSISTANCE PLATFORM  ·  MARK VIII", self)
        self.footer.setStyleSheet("color:#00dcff; font-family:Consolas; font-size:9pt; letter-spacing:6px; background:transparent;")
        self.footer.setGeometry(0, self.full_h - 24, self.full_w, 20)
        self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def update_status(self, state):
        self.current_state = state
        self.reactor.set_state(state)
        self.subtitle.setText(f"MARK VIII  ·  {STATE_LABEL.get(state, state.upper())}")
        self.waveform.set_active(state == "speaking")
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Deep black background
        p.fillRect(self.rect(), QColor(4, 8, 14, 250))
        # Subtle grid lines (very faint)
        p.setPen(QPen(QColor(0, 100, 140, 25), 1))
        for x in range(0, self.full_w, 60):
            p.drawLine(x, 0, x, self.full_h)
        for y in range(0, self.full_h, 60):
            p.drawLine(0, y, self.full_w, y)
        # Two horizontal cyan lines (top + bottom borders of the work area)
        p.setPen(QPen(CYAN, 2))
        p.drawLine(20, 158, self.full_w - 20, 158)
        p.drawLine(20, self.full_h - 34, self.full_w - 20, self.full_h - 34)
        # Corner brackets
        p.setPen(QPen(CYAN_BRIGHT, 2))
        for cx, cy in [(20, 20), (self.full_w - 20, 20),
                       (20, self.full_h - 20), (self.full_w - 20, self.full_h - 20)]:
            sx = -1 if cx < 100 else 1
            sy = -1 if cy < 100 else 1
            p.drawLine(cx, cy, cx + 28 * sx, cy)
            p.drawLine(cx, cy, cx, cy + 28 * sy)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.requestExit.emit()
        else:
            super().keyPressEvent(e)


# ═══════════════════════════════════════════════════════════════
# CONTROLLER — manages both modes + hotkey + event polling
# ═══════════════════════════════════════════════════════════════
class HudController:
    def __init__(self):
        self.compact = CompactHUD()
        self.immersive = None
        self.events_pos = 0
        self.compact.requestImmersive.connect(self.show_immersive)
        self.compact.requestHide.connect(self.hide_all)
        self.compact.requestQuit.connect(self._quit_jarvis)
        self.timer = QTimer(); self.timer.timeout.connect(self._poll); self.timer.start(150)
        self.show_timer = QTimer(); self.show_timer.timeout.connect(self._check_show_sentinel); self.show_timer.start(500)
        try:
            import keyboard
            keyboard.add_hotkey("windows+j", self._toggle_via_hotkey)
        except Exception as e:
            print(f"[HUD] global hotkey unavailable: {e}", flush=True)
        # HUD starts HIDDEN — user summons via tray/hotkey
        self.compact.hide()

    def _check_show_sentinel(self):
        sentinel = r"C:\Users\Dev\JARVIS\.hud_show"
        if os.path.exists(sentinel):
            try: os.remove(sentinel)
            except Exception: pass
            self._show_compact()

    def _show_compact(self):
        if self.immersive and self.immersive.isVisible():
            self.immersive.hide()
        self.compact.show()
        self.compact.raise_()
        self.compact.activateWindow()

    def _toggle_via_hotkey(self):
        QTimer.singleShot(0, self._toggle_state)

    def _toggle_state(self):
        if self.immersive and self.immersive.isVisible():
            self.immersive.hide()
            self.compact.hide()
        elif self.compact.isVisible():
            self.show_immersive()
        else:
            self.compact.show()
            self.compact.raise_()
            self.compact.activateWindow()

    def show_immersive(self):
        if self.immersive is None:
            self.immersive = ImmersiveHUD()
            self.immersive.requestExit.connect(self.hide_immersive)
        self.compact.hide()
        self.immersive.show()
        self.immersive.raise_()
        self.immersive.activateWindow()
        self.immersive.update_status(self.compact.reactor.state)

    def hide_immersive(self):
        if self.immersive: self.immersive.hide()
        self.compact.show()
        self.compact.raise_()

    def hide_all(self):
        self.compact.hide()
        if self.immersive: self.immersive.hide()

    def _quit_jarvis(self):
        try:
            with open(r"C:\Users\Dev\JARVIS\.shutdown", "w") as f:
                f.write(str(time.time()))
        except Exception: pass
        QApplication.quit()

    def _poll(self):
        if not os.path.exists(EVENTS_FILE): return
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
        except Exception: pass

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
            if self.immersive and self.immersive.isVisible():
                self.immersive.agent_row.update_agent(a, "working")
            for t in targets:
                if hasattr(t, "stream"): t.stream.add("agent_start", f"{a}: {evt.get('task','')[:60]}")
        elif kind == "agent_done":
            a = evt.get("agent", "")
            self.compact.agent_row.update_agent(a, "done")
            if self.immersive and self.immersive.isVisible():
                self.immersive.agent_row.update_agent(a, "done")
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
    # Auto-summon compact on first launch so user sees it immediately
    QTimer.singleShot(500, lambda: ctrl._show_compact())
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
