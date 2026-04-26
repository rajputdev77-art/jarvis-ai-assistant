"""
JARVIS HUD — floating glass overlay.
Reads C:\\Users\\Dev\\JARVIS\\hud_events.jsonl, renders state + thought stream live.
Run: python hud.py  (jarvis.py launches this automatically)
"""

import os
import sys
import json
import time
from collections import deque
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QRectF
from PyQt6.QtGui import (QPainter, QColor, QBrush, QPen, QFont, QPainterPath,
                         QLinearGradient, QFontMetrics)
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QHBoxLayout, QPushButton, QScrollArea,
                             QSizePolicy, QGraphicsDropShadowEffect)

EVENTS_FILE = r"C:\Users\Dev\JARVIS\hud_events.jsonl"

STATE_COLOURS = {
    "idle":      QColor(120, 130, 145),
    "listening": QColor(50,  220, 110),
    "thinking":  QColor(255, 190, 60),
    "speaking":  QColor(80,  170, 255),
    "working":   QColor(220, 100, 240),
}

STATE_LABEL = {
    "idle": "STANDBY", "listening": "LISTENING",
    "thinking": "THINKING", "speaking": "SPEAKING", "working": "EXECUTING",
}


class GlowDot(QWidget):
    """Pulsing state indicator dot."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(28, 28)
        self.color = STATE_COLOURS["idle"]
        self._pulse = 0.0
        self._dir = 1
        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(40)

    def _tick(self):
        self._pulse += 0.04 * self._dir
        if self._pulse >= 1.0: self._dir = -1
        if self._pulse <= 0.0: self._dir = 1
        self.update()

    def set_state(self, state):
        self.color = STATE_COLOURS.get(state, STATE_COLOURS["idle"])
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Outer glow
        glow = QColor(self.color)
        glow.setAlpha(int(60 + 80 * self._pulse))
        p.setBrush(QBrush(glow)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, 24, 24)
        # Solid core
        p.setBrush(QBrush(self.color))
        p.drawEllipse(8, 8, 12, 12)


class EventRow(QWidget):
    """One line in the thought stream."""
    def __init__(self, kind, text, timestamp):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 10, 2)
        layout.setSpacing(8)

        # Color tag by kind
        kind_colors = {
            "user_said":   "#5fc8ff",
            "speak":       "#ffd56b",
            "tool_call":   "#c876ff",
            "tool_result": "#7be0a8",
            "status":      "#9099a8",
            "shell":       "#ff8a65",
            "clipboard_signal": "#ff5677",
        }
        kind_labels = {
            "user_said":   "YOU ",
            "speak":       "JARVIS",
            "tool_call":   "TOOL",
            "tool_result": "  ↳ ",
            "status":      "stat",
            "shell":       "SHELL",
            "clipboard_signal": "CLIP",
        }
        color = kind_colors.get(kind, "#aaa")
        label = QLabel(kind_labels.get(kind, kind[:5].upper()))
        label.setStyleSheet(f"color:{color}; font-family:Consolas; font-size:9pt; font-weight:bold;")
        label.setFixedWidth(48)
        layout.addWidget(label)

        body = QLabel(text)
        body.setWordWrap(True)
        body.setStyleSheet("color:#e6e8ee; font-family:'Segoe UI'; font-size:9pt;")
        body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(body, 1)


class JarvisHUD(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS HUD")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(440, 540)

        self.events = deque(maxlen=80)
        self.current_state = "idle"
        self._drag_pos = None
        self._file_pos = 0
        self._collapsed = False

        self._build_ui()
        self._position_top_right()

        # Tail the events file
        timer = QTimer(self)
        timer.timeout.connect(self._poll_events)
        timer.start(150)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(56)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 8, 10, 8)
        h_layout.setSpacing(10)

        self.dot = GlowDot()
        h_layout.addWidget(self.dot)

        title_box = QVBoxLayout(); title_box.setSpacing(0)
        self.title = QLabel("J.A.R.V.I.S.")
        self.title.setStyleSheet("color:#f4f5f8; font-family:'Segoe UI'; "
                                 "font-size:13pt; font-weight:bold; letter-spacing:2px;")
        self.subtitle = QLabel("STANDBY")
        self.subtitle.setStyleSheet("color:#8090a8; font-family:Consolas; font-size:8pt; letter-spacing:1px;")
        title_box.addWidget(self.title); title_box.addWidget(self.subtitle)
        h_layout.addLayout(title_box, 1)

        # Min/Close
        btn_min = QPushButton("—"); btn_min.setFixedSize(24, 24)
        btn_min.setStyleSheet(self._btn_style())
        btn_min.clicked.connect(self._toggle_collapse)
        h_layout.addWidget(btn_min)

        btn_close = QPushButton("✕"); btn_close.setFixedSize(24, 24)
        btn_close.setStyleSheet(self._btn_style())
        btn_close.clicked.connect(self.close)
        h_layout.addWidget(btn_close)

        outer.addWidget(header)

        # Divider
        div = QWidget(); div.setFixedHeight(1)
        div.setStyleSheet("background-color:#2a3140;")
        outer.addWidget(div)

        # Currently-doing strip
        self.now_label = QLabel("Awaiting wake word…")
        self.now_label.setStyleSheet(
            "color:#bcc4d4; font-family:'Segoe UI'; font-size:9pt; "
            "padding:6px 14px; background-color:#161a23;"
        )
        self.now_label.setWordWrap(True)
        outer.addWidget(self.now_label)

        # Stream area (scrollable)
        self.stream_container = QWidget()
        self.stream_layout = QVBoxLayout(self.stream_container)
        self.stream_layout.setContentsMargins(0, 4, 0, 4)
        self.stream_layout.setSpacing(2)
        self.stream_layout.addStretch()

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.stream_container)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: transparent; width: 6px; }
            QScrollBar::handle:vertical { background: #3a4458; border-radius: 3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        outer.addWidget(self.scroll, 1)

        # Footer
        footer = QLabel("drag to move · ✕ to hide · Jarvis is always listening")
        footer.setStyleSheet("color:#5a6478; font-family:Consolas; font-size:7.5pt; "
                             "padding:4px 14px; background-color:#0e1119;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(footer)

    def _btn_style(self):
        return ("""QPushButton {
            background-color: rgba(255,255,255,0.05);
            color: #b0b8c8; border: none; border-radius: 4px;
            font-family: 'Segoe UI'; font-size: 11pt;
        } QPushButton:hover {
            background-color: rgba(255,255,255,0.12); color: #fff;
        }""")

    def _position_top_right(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 24, screen.top() + 60)

    def _toggle_collapse(self):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self.scroll.hide(); self.now_label.hide()
            self.setMinimumHeight(56); self.resize(self.width(), 56)
        else:
            self.scroll.show(); self.now_label.show()
            self.setMinimumHeight(540); self.resize(self.width(), 540)

    # Painting — frosted glass background
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        # Background
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(20, 24, 34, 235))
        grad.setColorAt(1.0, QColor(14, 17, 25, 235))
        p.fillPath(path, QBrush(grad))
        # Border
        pen = QPen(QColor(60, 75, 100, 180)); pen.setWidth(1)
        p.setPen(pen); p.drawPath(path)
        # Accent bar (state-coloured)
        accent = STATE_COLOURS.get(self.current_state, STATE_COLOURS["idle"])
        accent.setAlpha(180)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(accent))
        p.drawRoundedRect(0, 0, 4, self.height(), 2, 2)

    # Drag-to-move
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and (e.buttons() & Qt.MouseButton.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    # Event polling
    def _poll_events(self):
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
                try:
                    evt = json.loads(line)
                except Exception:
                    continue
                self._handle(evt)
        except Exception:
            pass

    def _handle(self, evt):
        kind = evt.get("kind", "")
        if kind == "status":
            state = evt.get("state", "idle")
            self.current_state = state
            self.dot.set_state(state)
            self.subtitle.setText(STATE_LABEL.get(state, state.upper()))
            self.update()
            return

        # Build display text
        if kind == "user_said":
            text = evt.get("text", "")
            self.now_label.setText(f"You said: \"{text}\"")
        elif kind == "speak":
            text = evt.get("text", "")
            self.now_label.setText(f"Jarvis: \"{text}\"")
        elif kind == "tool_call":
            name = evt.get("name", "")
            args = evt.get("args", {})
            args_short = json.dumps(args, ensure_ascii=False)[:80]
            text = f"{name}({args_short})"
            self.now_label.setText(f"Calling tool · {name}  (step {evt.get('step', '?')})")
        elif kind == "tool_result":
            text = f"{evt.get('name','')} → {evt.get('result','')[:200]}"
        elif kind == "shell":
            text = f"$ {evt.get('command','')[:200]}"
        elif kind == "clipboard_signal":
            text = f"Stack trace detected on clipboard ({evt.get('length')} chars)"
        else:
            text = json.dumps(evt)

        ts = datetime.fromtimestamp(evt.get("t", time.time())).strftime("%H:%M:%S")
        self._add_row(kind, text, ts)

    def _add_row(self, kind, text, ts):
        row = EventRow(kind, text, ts)
        # Insert before the trailing stretch
        self.stream_layout.insertWidget(self.stream_layout.count() - 1, row)
        # Trim old rows
        while self.stream_layout.count() > 81:  # 80 rows + stretch
            old = self.stream_layout.itemAt(0).widget()
            if old:
                old.setParent(None)
            else:
                break
        # Auto-scroll to bottom
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()))


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    hud = JarvisHUD()
    hud.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
