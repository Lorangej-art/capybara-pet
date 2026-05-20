# -*- coding: utf-8 -*-
"""
桌面宠物 —— 卡皮巴拉（水豚），头顶橘子
精灵图优先：assets/spritesheet.webp → 纯代码回退。
"""

import sys
import os
import random
import math
import platform
from dataclasses import dataclass
from typing import List, Dict

from PyQt5.QtWidgets import QApplication, QWidget, QMenu, QAction
from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPainterPath,
    QFontMetrics, QLinearGradient, QRadialGradient, QPixmap,
)

# ═══════════════════════════════════════════════════════════════
#  精灵图规格
# ═══════════════════════════════════════════════════════════════

COLS, ROWS = 8, 9
FRAME_W, FRAME_H = 192, 208
SHEET_W, SHEET_H = FRAME_W * COLS, FRAME_H * ROWS   # 1536×1872

TICK_MS = 20  # 基础定时器间隔

# 行号映射（严格按 README 顺序）
ROW_MAP: Dict[str, int] = {
    "idle":          0,
    "running_right": 1,
    "running_left":  2,
    "waving":        3,
    "jumping":       4,
    "failed":        5,
    "waiting":       6,
    "running":       7,
    "review":        8,
}

# 每个状态每几 tick（20ms）切一帧
FRAME_TICKS: Dict[str, int] = {
    "idle":          6,   # 120ms
    "running_right": 4,   #  80ms
    "running_left":  4,   #  80ms
    "waving":        5,   # 100ms
    "jumping":       4,   #  80ms
    "failed":        6,   # 120ms
    "waiting":       8,   # 160ms
    "running":       3,   #  60ms
    "review":        5,   # 100ms
}

# 每个状态的实际帧数（精灵图各行动画列数不同）
FRAME_COUNT: Dict[str, int] = {
    "idle":          6,
    "running_right": 8,
    "running_left":  8,
    "waving":        4,
    "jumping":       5,
    "failed":        8,
    "waiting":       6,
    "running":       6,
    "review":        6,
}

# 乒乓播放状态（非方向性动画，避免 7→0 硬切闪烁）
PINGPONG_STATES = {"idle", "waving", "jumping", "waiting", "review"}

# 单次播放状态（播放到最后一帧后停止）
ONESHOT_STATES = {"failed"}

# 窗口尺寸
# 窗口尺寸（宽于精灵图，给气泡留空间）
WIN_W, WIN_H = 350, FRAME_H

# 回退模式
FB_W, FB_H = 280, 380

# 移动速度 (px/tick, 20ms)
WALK_SPEED = 1.6    # 80 px/s
RUN_SPEED  = 3.5    # 175 px/s


# ═══════════════════════════════════════════════════════════════
#  短语
# ═══════════════════════════════════════════════════════════════

PHRASES: Dict[str, List[str]] = {
    "idle": [
        "今天天气真舒服～", "橘子……想吃橘子……", "呼噜呼噜……",
        "诶？你在看我吗？", "慢慢来，不急～", "卡皮巴拉～",
        "头顶橘子不掉下来！", "午饭吃了吗？",
    ],
    "running_right": ["哒哒哒……", "散步散步～", "去哪儿好呢？", "这边看看～"],
    "running_left":  ["走走走～", "散个步～", "那边有什么？", "慢慢走……"],
    "waving":        ["嘻嘻～好舒服！", "再摸摸嘛～", "开心！", "最喜欢被摸头了！"],
    "jumping":       ["好吃好吃！", "橘子真甜～", "再来一颗！", "嘎嘣嘎嘣～"],
    "failed":        ["啊！失败了……", "呜……", "怎么会这样！", "再试一次！"],
    "waiting":       ["呼……呼……", "zzzZZZ……", "温泉好暖和……", "咕噜咕噜……"],
    "running":       ["冲啊！", "快跑快跑！", "让开让开～", "嗖——"],
    "review":        ["嗯……让我想想……", "等一下哦～", "考虑一下……", "唔……"],
}

# 回退模式颜色
C_BODY_DARK  = QColor(101, 67, 33)
C_BODY       = QColor(139, 90, 43)
C_BODY_LIGHT = QColor(160, 110, 60)
C_BELLY      = QColor(195, 150, 100)
C_HEAD       = QColor(150, 100, 55)
C_HEAD_LIGHT = QColor(175, 125, 75)
C_EAR_INNER  = QColor(200, 155, 110)
C_EYE        = QColor(30, 20, 10)
C_EYE_HL     = QColor(255, 255, 255)
C_NOSE       = QColor(45, 30, 15)
C_MOUTH      = QColor(60, 40, 20)
C_ORANGE     = QColor(255, 140, 0)
C_ORANGE_D   = QColor(220, 110, 0)
C_LEAF       = QColor(34, 139, 34)
C_LEAF_D     = QColor(20, 100, 20)
C_WATER      = QColor(100, 180, 220, 160)
C_BUBBLE     = QColor(180, 220, 255, 180)
C_ZZZ        = QColor(100, 140, 200)
C_CRUMB      = QColor(255, 160, 50)
C_SPEECH_BG  = QColor(255, 255, 255, 230)
C_SPEECH_BORDER = QColor(180, 180, 180)

PET_CX, PET_BASE_Y = 140, 290


# ═══════════════════════════════════════════════════════════════
#  辅助
# ═══════════════════════════════════════════════════════════════

def _get_font(size: int = 10) -> QFont:
    system = platform.system()
    if system == "Windows":
        names = ["Microsoft YaHei", "SimHei", "SimSun"]
    elif system == "Darwin":
        names = ["PingFang SC", "Heiti SC", "STHeiti"]
    else:
        names = ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "DejaVu Sans"]
    font = QFont()
    for name in names:
        font.setFamily(name)
        if font.exactMatch():
            break
    font.setPixelSize(size)
    return font


@dataclass
class Particle:
    x: float; y: float; vx: float; vy: float
    life: float; size: float; kind: str; text: str = ""


# ═══════════════════════════════════════════════════════════════
#  主窗口
# ═══════════════════════════════════════════════════════════════

class CapybaraPet(QWidget):

    def __init__(self):
        super().__init__()

        # ── 精灵图加载（一次性切割） ─────────────────
        self._frames: List[List[QPixmap]] = []
        self._use_sprite = self._load_spritesheet()

        self._ww = WIN_W if self._use_sprite else FB_W
        self._wh = WIN_H if self._use_sprite else FB_H

        # ── 窗口 ────────────────────────────────────
        self.setWindowTitle("卡皮巴拉 — 桌面宠物")
        self.setFixedSize(self._ww, self._wh)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)

        # ── 状态 ────────────────────────────────────
        self._state = "idle"
        # ★ 每个状态独立维护播放进度，切换时不重置
        self.state_frames: Dict[str, int] = {
            s: 0 for s in ROW_MAP.keys()}
        # ★ 乒乓播放方向：1=正向，-1=反向（仅非方向性动画）
        self._play_dir: Dict[str, int] = {
            s: 1 for s in PINGPONG_STATES}
        self.tick_counter = 0         # 实际切帧用计数器
        self._walk_dir = 1            # 1=右, -1=左（running 用）
        self._frame_hold = 0          # 方向性动画 7→0 缓冲计数器
        self._x_float = 0.0           # 浮点 X 坐标（避免子像素移动丢失）

        # ── 回退模式变量 ────────────────────────────
        self._anim_frame = 0
        self._bob_offset = 0.0
        self._mouth_open = 0.0
        self._is_blinking = False
        self._blink_timer = random.randint(60, 180)
        self._particles: List[Particle] = []

        # ── 气泡 ───────────────────────────────────
        self._speech_text = ""
        self._speech_timer = 0

        # ── 拖拽 ───────────────────────────────────
        self._dragging = False
        self._drag_offset = QPoint()
        self._prev_drag_x = 0
        self._drag_moved = False

        # ── 随机行为 ──────────────────────────────
        self._idle_action_timer = random.randint(300, 700)

        # ── 定时器（固定 20ms） ─────────────────────
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(TICK_MS)

        self._say("idle")

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - FRAME_W - 50,
                   screen.bottom() - self._wh - 100)
        self._x_float = float(self.x())

    # ═══════════════════════════════════════════════════════════
    #  资源路径 & 精灵图加载（一次性切割）
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _asset_path(filename: str) -> str:
        base = sys._MEIPASS if getattr(sys, 'frozen', False) \
               else os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "assets", filename)

    def _load_spritesheet(self) -> bool:
        path = self._asset_path("spritesheet.webp")
        if not os.path.exists(path):
            print("[lulu_pet] 精灵图缺失，回退纯代码绘制")
            return False
        sheet = QPixmap(path)
        if sheet.isNull() or sheet.width() != SHEET_W or sheet.height() != SHEET_H:
            print("[lulu_pet] 精灵图无效，回退纯代码绘制")
            return False
        # ★ 一次性切割 72 帧，之后绝不再 copy
        for r in range(ROWS):
            row_frames = []
            for c in range(COLS):
                row_frames.append(
                    sheet.copy(c * FRAME_W, r * FRAME_H, FRAME_W, FRAME_H))
            self._frames.append(row_frames)
        print(f"[lulu_pet] 精灵图 {ROWS}×{COLS}={ROWS*COLS} 帧就绪")
        return True

    # ═══════════════════════════════════════════════════════════
    #  状态管理
    # ═══════════════════════════════════════════════════════════

    def set_state(self, state: str, duration: int = 0):
        """切换状态。oneshot 状态重置帧进度，其余从上次继续。"""
        self._state = state
        self.tick_counter = 0
        self._frame_hold = 0
        if state in ONESHOT_STATES:
            self.state_frames[state] = 0
        self._particles.clear()
        self._mouth_open = 0.0
        self._bob_offset = 0.0
        self._is_blinking = False
        self._blink_timer = random.randint(60, 180)

        self._say(state)

        if duration > 0:
            QTimer.singleShot(duration,
                              lambda s=state: self._auto_exit(s))

    def _auto_exit(self, expected: str):
        if self._dragging:
            return
        if self._state == expected:
            self.set_state("idle")

    # ═══════════════════════════════════════════════════════════
    #  对话气泡
    # ═══════════════════════════════════════════════════════════

    def _say(self, state: str):
        pool = PHRASES.get(state, PHRASES["idle"])
        self._speech_text = random.choice(pool)
        self._speech_timer = random.randint(120, 280)

    # ═══════════════════════════════════════════════════════════
    #  当前帧（从该状态的独立进度读取）
    # ═══════════════════════════════════════════════════════════
    #  主循环（20ms 间隔）
    # ═══════════════════════════════════════════════════════════

    def _on_tick(self):
        self._anim_frame += 1

        # ── 精灵图帧切换（按每个状态的帧间隔） ──────
        if self._use_sprite:
            interval = FRAME_TICKS.get(self._state, 6)
            self.tick_counter += 1
            if self.tick_counter >= interval:
                self.tick_counter = 0
                st = self._state
                nf = FRAME_COUNT.get(st, COLS)
                if st in self._play_dir:
                    # 乒乓播放：0→1→...→(nf-1)→(nf-2)→...→1→0
                    col = self.state_frames[st]
                    d = self._play_dir[st]
                    nxt = col + d
                    if nxt >= nf:
                        nxt = nf - 2
                        self._play_dir[st] = -1
                    elif nxt < 0:
                        nxt = 1
                        self._play_dir[st] = 1
                    self.state_frames[st] = nxt
                elif st in ONESHOT_STATES:
                    # 单次播放：0→1→...→(nf-1)，停在最后一帧
                    col = self.state_frames[st]
                    if col < nf - 1:
                        self.state_frames[st] = col + 1
                else:
                    # 方向性动画：循环 0..(nf-1)，末帧→0 时多停留一帧
                    if self._frame_hold > 0:
                        self._frame_hold -= 1
                    else:
                        col = self.state_frames[st]
                        nxt = (col + 1) % nf
                        self.state_frames[st] = nxt
                        if col == nf - 1 and nxt == 0:
                            self._frame_hold = 1

        # ── 回退眨眼 ─────────────────────────────────
        if not self._use_sprite:
            if self._state in ("idle", "waving", "running_right", "running_left"):
                if self._is_blinking:
                    self._blink_timer -= 1
                    if self._blink_timer <= 0:
                        self._is_blinking = False
                        self._blink_timer = random.randint(60, 180)
                else:
                    self._blink_timer -= 1
                    if self._blink_timer <= 0:
                        self._is_blinking = True
                        self._blink_timer = 4

        # ── 气泡倒计时 ───────────────────────────────
        if self._speech_timer > 0:
            self._speech_timer -= 1
        elif self._state == "idle" and random.random() < 0.001:
            self._say("idle")

        # ── 状态逻辑 ─────────────────────────────────
        st = self._state

        if st == "idle":
            if not self._use_sprite:
                self._bob_offset = math.sin(self._anim_frame * 0.015) * 1.5
            self._idle_action_timer -= 1
            if self._idle_action_timer <= 0:
                self._idle_action_timer = random.randint(500, 1200)
                r = random.random()
                if r < 0.25:
                    s = random.choice(["running_right", "running_left"])
                    self.set_state(s, duration=random.randint(4000, 8000))
                elif r < 0.40:
                    self.set_state("waiting", duration=random.randint(6000, 12000))

        elif st == "running" and not self._dragging:
            self._move_run()

        elif st in ("running_right", "running_left") and not self._dragging:
            self._move_walk()

        elif st == "waiting" and not self._use_sprite:
            self._spawn_particles_sleep()

        elif st == "waving" and not self._use_sprite:
            self._bob_offset = math.sin(self._anim_frame * 0.075) * 3.0

        elif st == "jumping" and not self._use_sprite:
            self._mouth_open = abs(math.sin(self._anim_frame * 0.1))
            self._spawn_particles_eat()

        # ── 更新粒子 ─────────────────────────────────
        if not self._use_sprite:
            self._update_particles()

        self.update()

    def _move_walk(self):
        """running_right / running_left 移动 + 碰墙反弹"""
        d = 1 if self._state == "running_right" else -1
        self._x_float += WALK_SPEED * d
        screen = QApplication.primaryScreen().availableGeometry()
        if self._x_float < screen.left():
            self._x_float = float(screen.left())
            self.set_state("running_right", duration=3000)
        elif self._x_float + FRAME_W > screen.right():
            self._x_float = float(screen.right() - FRAME_W)
            self.set_state("running_left", duration=3000)
        self.move(int(self._x_float), self.y())

    def _move_run(self):
        """running 移动 + 碰墙反弹（翻转 walk_dir）"""
        self._x_float += RUN_SPEED * self._walk_dir
        screen = QApplication.primaryScreen().availableGeometry()
        if self._x_float < screen.left():
            self._x_float = float(screen.left())
            self._walk_dir = 1
        elif self._x_float + FRAME_W > screen.right():
            self._x_float = float(screen.right() - FRAME_W)
            self._walk_dir = -1
        self.move(int(self._x_float), self.y())

    # ── 回退粒子 ──────────────────────────────────────

    def _spawn_particles_sleep(self):
        if random.random() < 0.25:
            self._particles.append(Particle(
                random.uniform(70, 210), 270,
                random.uniform(-0.3, 0.3), random.uniform(-1.5, -0.6),
                1.0, random.uniform(4, 10), "bubble"))
        if random.random() < 0.06:
            self._particles.append(Particle(
                random.uniform(150, 190), random.uniform(80, 110),
                random.uniform(0.2, 0.6), random.uniform(-1.2, -0.6),
                1.0, random.uniform(10, 16), "zzz",
                random.choice(["Z", "z", "Z"])))

    def _spawn_particles_eat(self):
        if random.random() < 0.35:
            self._particles.append(Particle(
                random.uniform(120, 160), random.uniform(185, 195),
                random.uniform(-0.5, 0.5), random.uniform(0.4, 1.0),
                1.0, random.uniform(2, 5), "crumb"))

    def _update_particles(self):
        for p in self._particles:
            p.x += p.vx; p.y += p.vy; p.life -= 0.015
            if p.kind == "bubble":
                p.vx += random.uniform(-0.05, 0.05)
            elif p.kind == "crumb":
                p.vy += 0.04
        self._particles = [p for p in self._particles if p.life > 0]

    # ═══════════════════════════════════════════════════════════
    #  绘制入口
    # ═══════════════════════════════════════════════════════════

    def paintEvent(self, event):
        if self._use_sprite:
            self._paint_sprite()
        else:
            self._paint_fallback()

    # ═══════════════════════════════════════════════════════════
    #  精灵图绘制（极简：取帧 → drawPixmap → 气泡）
    # ═══════════════════════════════════════════════════════════

    def _paint_sprite(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # ★ 第 1 行立刻画帧，零延迟——前面不做任何判断、函数调用
        row = ROW_MAP[self._state]
        col = self.state_frames[self._state]
        frame = self._frames[row][col]
        painter.drawPixmap(0, 0, frame)

        if self._speech_text and self._speech_timer > 0:
            self._draw_bubble_sprite(painter)

        painter.end()

    def _draw_bubble_sprite(self, painter: QPainter):
        fm = QFontMetrics(_get_font(10))
        text = self._speech_text
        tw = fm.horizontalAdvance(text)
        tw = max(tw, 24)
        bw, bh = tw + 16, 24
        bx = 120
        by = 6

        path = QPainterPath()
        path.addRoundedRect(QRectF(bx, by, bw, bh), 8, 8)
        tri = bx + bw * 0.35
        ty = by + bh
        path.moveTo(tri - 5, ty)
        path.lineTo(tri, ty + 6)
        path.lineTo(tri + 5, ty)
        path.closeSubpath()

        painter.setBrush(QBrush(C_SPEECH_BG))
        painter.setPen(QPen(C_SPEECH_BORDER, 1))
        painter.drawPath(path)
        painter.setPen(QColor(40, 40, 40))
        painter.setFont(_get_font(10))
        painter.drawText(QRectF(bx, by, bw, bh), Qt.AlignCenter, text)

    # ═══════════════════════════════════════════════════════════
    #  回退模式：纯 QPainter 绘制
    # ═══════════════════════════════════════════════════════════

    def _paint_fallback(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        ox, oy = 0.0, self._bob_offset

        if self._state == "waiting":
            self._draw_water(painter)
        for p in self._particles:
            if p.kind == "bubble":
                self._draw_particle(painter, p)

        self._draw_capybara(painter, ox, oy)

        for p in self._particles:
            if p.kind in ("zzz", "crumb"):
                self._draw_particle(painter, p)
        if self._speech_text and self._speech_timer > 0:
            self._draw_bubble_fb(painter)
        painter.end()

    def _draw_capybara(self, p: QPainter, ox: float, oy: float):
        if self._state == "waiting":
            self._draw_sleep(p, ox, oy)
        else:
            self._draw_stand(p, ox, oy)

    def _draw_stand(self, p: QPainter, ox: float, oy: float):
        cx, by = PET_CX + ox, PET_BASE_Y + oy
        self._leg(p, cx - 38, by - 5, 22, 16)
        self._leg(p, cx + 16, by - 5, 22, 16)

        bp = QPainterPath()
        bp.addRoundedRect(QRectF(cx - 55, by - 70, 110, 72), 30, 30)
        g = QLinearGradient(cx - 55, by - 70, cx - 55, by - 70 + 72)
        g.setColorAt(0, C_BODY_LIGHT); g.setColorAt(0.5, C_BODY)
        g.setColorAt(1, C_BODY_DARK)
        p.setBrush(QBrush(g)); p.setPen(QPen(C_BODY_DARK, 2))
        p.drawPath(bp)

        bp2 = QPainterPath()
        bp2.addRoundedRect(QRectF(cx - 35, by - 58, 70, 45), 20, 20)
        p.setBrush(QBrush(C_BELLY)); p.setPen(Qt.NoPen); p.drawPath(bp2)

        lo = ro = 0.0
        if self._state in ("running_right", "running_left"):
            ph = self._anim_frame * 0.075
            lo = math.sin(ph) * 5; ro = math.sin(ph + math.pi) * 5
        self._leg(p, cx - 38, by - 5 + lo, 22, 16)
        self._leg(p, cx + 16, by - 5 + ro, 22, 16)

        self._draw_head(p, cx, by - 85 + oy)
        self._draw_orange(p, cx, by - 127 + oy)

    def _draw_sleep(self, p: QPainter, ox: float, oy: float):
        cx, by = PET_CX + ox, PET_BASE_Y + oy + 25
        bp = QPainterPath()
        bp.addRoundedRect(QRectF(cx - 65, by - 45, 130, 55), 25, 25)
        g = QLinearGradient(cx - 65, by - 45, cx - 65, by - 45 + 55)
        g.setColorAt(0, C_BODY_LIGHT); g.setColorAt(0.6, C_BODY)
        g.setColorAt(1, C_BODY_DARK)
        p.setBrush(QBrush(g)); p.setPen(QPen(C_BODY_DARK, 2)); p.drawPath(bp)

        bp2 = QPainterPath()
        bp2.addRoundedRect(QRectF(cx - 40, by - 35, 80, 32), 15, 15)
        p.setBrush(QBrush(C_BELLY)); p.setPen(Qt.NoPen); p.drawPath(bp2)

        self._leg(p, cx - 45, by - 8, 18, 12)
        self._leg(p, cx + 27, by - 8, 18, 12)
        self._leg(p, cx - 42, by - 5, 18, 14)
        self._leg(p, cx + 24, by - 5, 18, 14)

        self._draw_head(p, cx + 8, by - 50 + oy, sleepy=True)
        self._draw_orange(p, cx + 8, by - 88 + oy)

    def _draw_head(self, p: QPainter, cx: float, cy: float,
                   sleepy: bool = False):
        for ex in (-30, 30):
            p.setBrush(QBrush(C_HEAD)); p.setPen(QPen(C_BODY_DARK, 1.5))
            p.drawEllipse(QPoint(int(cx + ex), int(cy - 8)), 12, 14)
            p.setBrush(QBrush(C_EAR_INNER)); p.setPen(Qt.NoPen)
            p.drawEllipse(QPoint(int(cx + ex), int(cy - 8)), 7, 9)

        g = QRadialGradient(cx, cy - 5, 42)
        g.setColorAt(0, C_HEAD_LIGHT); g.setColorAt(1, C_HEAD)
        p.setBrush(QBrush(g)); p.setPen(QPen(C_BODY_DARK, 2))
        p.drawEllipse(QPoint(int(cx), int(cy)), 42, 38)

        ey = cy - 6
        if sleepy:
            for ex in (-14, 14):
                p.setPen(QPen(C_EYE, 2.5)); p.setBrush(Qt.NoBrush)
                p.drawArc(QRectF(int(cx+ex-7), int(ey-4), 14, 10),
                           180*16, 180*16)
        elif self._state == "waving":
            for ex in (-14, 14):
                p.setPen(QPen(C_EYE, 2.5))
                xc = int(cx + ex); y1, y2 = int(ey+3), int(ey-3)
                p.drawLine(xc-5, y1, xc, y2); p.drawLine(xc, y2, xc+5, y1)
        elif self._is_blinking:
            for ex in (-14, 14):
                p.setPen(QPen(C_EYE, 2.5))
                p.drawLine(int(cx+ex-6), int(ey+1), int(cx+ex+6), int(ey+1))
        else:
            for ex in (-14, 14):
                p.setBrush(QBrush(Qt.white)); p.setPen(QPen(C_EYE, 1.5))
                p.drawEllipse(QPoint(int(cx+ex), int(ey)), 7, 8)
                p.setBrush(QBrush(C_EYE)); p.setPen(Qt.NoPen)
                p.drawEllipse(QPoint(int(cx+ex+1), int(ey)), 4, 5)
                p.setBrush(QBrush(C_EYE_HL))
                p.drawEllipse(QPoint(int(cx+ex-1), int(ey-3)), 2, 2)

        ny = cy + 14
        p.setBrush(QBrush(C_BELLY)); p.setPen(Qt.NoPen)
        p.drawEllipse(QPoint(int(cx), int(ny-1)), 22, 16)
        p.setBrush(QBrush(C_NOSE))
        p.drawEllipse(QPoint(int(cx-5), int(ny)), 3, 2.5)
        p.drawEllipse(QPoint(int(cx+5), int(ny)), 3, 2.5)

        my = ny + 8; st = self._state
        if st == "jumping":
            mo = self._mouth_open * 6
            p.setPen(QPen(C_MOUTH, 2))
            p.setBrush(QBrush(QColor(80,30,10,150)))
            p.drawEllipse(QPoint(int(cx), int(my+mo/2)), 7, 4+mo)
        elif st == "waving":
            p.setPen(QPen(C_MOUTH, 2)); p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(int(cx-8), int(my-4), 16, 10), 0, 180*16)
        elif sleepy:
            p.setPen(QPen(C_MOUTH, 1.5))
            p.setBrush(QBrush(QColor(80,30,10,100)))
            p.drawEllipse(QPoint(int(cx), int(my+1)), 4, 3)
        else:
            p.setPen(QPen(C_MOUTH, 1.8)); p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(int(cx-7), int(my-1), 14, 8), 0, 180*16)

    def _leg(self, p: QPainter, x: float, y: float, w: float, h: float):
        pp = QPainterPath()
        pp.addRoundedRect(QRectF(x, y, w, h), 6, 6)
        g = QLinearGradient(x, y, x, y+h)
        g.setColorAt(0, C_BODY_LIGHT); g.setColorAt(1, C_BODY_DARK)
        p.setBrush(QBrush(g)); p.setPen(QPen(C_BODY_DARK, 1.5)); p.drawPath(pp)
        p.setPen(QPen(C_BODY_DARK.darker(130), 1))
        p.drawLine(int(x+w/2), int(y+h-2), int(x+w/2), int(y+h))

    def _draw_orange(self, p: QPainter, cx: float, cy: float):
        r = 17
        g = QRadialGradient(cx-4, cy-4, r)
        g.setColorAt(0, QColor(255,180,60)); g.setColorAt(0.6, C_ORANGE)
        g.setColorAt(1, C_ORANGE_D)
        p.setBrush(QBrush(g)); p.setPen(QPen(C_ORANGE_D.darker(120), 2))
        p.drawEllipse(QPoint(int(cx), int(cy)), r, r)
        p.setPen(QPen(QColor(255,200,100,80), 0.8))
        for a in (-30, 0, 25):
            ra = math.radians(a)
            x1 = cx + math.cos(ra)*(r-5); y1 = cy + math.sin(ra)*(r-5)
            p.drawLine(int(x1), int(y1),
                        int(cx-math.cos(ra)*(r-5)), int(cy-math.sin(ra)*(r-5)))
        lx, ly = cx+r-4, cy-r+2
        lp = QPainterPath(); lp.moveTo(lx, ly)
        lp.quadTo(lx+14, ly-12, lx+8, ly-16)
        lp.quadTo(lx+3, ly-7, lx-2, ly+2); lp.closeSubpath()
        lg = QLinearGradient(lx, ly, lx+8, ly-16)
        lg.setColorAt(0, C_LEAF); lg.setColorAt(1, C_LEAF_D)
        p.setBrush(QBrush(lg)); p.setPen(QPen(C_LEAF_D, 1)); p.drawPath(lp)
        p.setPen(QPen(QColor(60,100,30), 2))
        p.drawLine(int(cx+r/2), int(cy-r), int(lx), int(ly))

    def _draw_water(self, p: QPainter):
        wy = 305
        for i in range(8):
            a = int(80+math.sin(self._anim_frame*0.025+i)*30)
            p.setPen(QPen(QColor(80,170,210,a), 2))
            wv = wy+math.sin(self._anim_frame*0.02+i*0.8)*5
            p.drawLine(int(30+i*30), int(wv), int(55+i*30), int(wv))
        wp = QPainterPath(); wp.addRoundedRect(QRectF(20,wy+5,240,40),10,10)
        p.setBrush(QBrush(C_WATER)); p.setPen(Qt.NoPen); p.drawPath(wp)

    def _draw_particle(self, p: QPainter, pt: Particle):
        a = int(255*pt.life)
        if pt.kind == "bubble":
            c = QColor(C_BUBBLE.red(), C_BUBBLE.green(), C_BUBBLE.blue(),
                        min(a, C_BUBBLE.alpha()))
            p.setBrush(QBrush(c)); p.setPen(QPen(c.lighter(130), 1))
            p.drawEllipse(QPoint(int(pt.x), int(pt.y)),
                           int(pt.size/2), int(pt.size/2))
        elif pt.kind == "zzz":
            p.setPen(QPen(QColor(C_ZZZ.red(), C_ZZZ.green(),
                                  C_ZZZ.blue(), a), 2))
            p.setFont(_get_font(int(pt.size)))
            p.drawText(QPoint(int(pt.x), int(pt.y)), pt.text)
        elif pt.kind == "crumb":
            c = QColor(C_CRUMB.red(), C_CRUMB.green(), C_CRUMB.blue(), a)
            p.setBrush(QBrush(c)); p.setPen(Qt.NoPen)
            p.drawEllipse(QPoint(int(pt.x), int(pt.y)),
                           int(pt.size), int(pt.size))

    def _draw_bubble_fb(self, p: QPainter):
        fm = QFontMetrics(_get_font(10))
        text = self._speech_text
        tw = fm.horizontalAdvance(text)
        if tw > 180: text = text[:12]+"…"; tw = fm.horizontalAdvance(text)
        tw = max(tw, 30); bw, bh = tw+24, 30
        bx = PET_CX - bw/2; by = 15
        bp = QPainterPath(); bp.addRoundedRect(QRectF(bx,by,bw,bh),12,12)
        bp.moveTo(PET_CX-8, by+bh); bp.lineTo(PET_CX, by+bh+10)
        bp.lineTo(PET_CX+8, by+bh); bp.closeSubpath()
        p.setBrush(QBrush(C_SPEECH_BG)); p.setPen(QPen(C_SPEECH_BORDER,1))
        p.drawPath(bp)
        p.setPen(QColor(40,40,40)); p.setFont(_get_font(10))
        p.drawText(QRectF(bx,by,bw,bh), Qt.AlignCenter, text)

    # ═══════════════════════════════════════════════════════════
    #  鼠标
    # ═══════════════════════════════════════════════════════════

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            self._prev_drag_x = event.globalPos().x()
            self._drag_moved = False

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        dx = event.globalPos().x() - self._prev_drag_x
        if abs(dx) > 3:
            self._drag_moved = True
            new_dir = 1 if dx > 0 else -1
            if new_dir != self._walk_dir:
                self._walk_dir = new_dir
            s = "running_right" if dx > 0 else "running_left"
            if self._state != s:
                self.set_state(s)
        self._prev_drag_x = event.globalPos().x()
        self.move(event.globalPos() - self._drag_offset)
        self._x_float = float(self.x())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._x_float = float(self.x())
            if self._drag_moved:
                self.set_state("idle")

    # ═══════════════════════════════════════════════════════════
    #  右键菜单（严格按 README 顺序，分隔线分组）
    # ═══════════════════════════════════════════════════════════

    def contextMenuEvent(self, event):
        m = QMenu(self)
        m.setStyleSheet("""
            QMenu{background:#fff8f0;border:2px solid #cba;border-radius:8px;
                  padding:4px;font-size:13px;}
            QMenu::item{padding:6px 30px 6px 16px;border-radius:4px;}
            QMenu::item:selected{background:#ffe0b0;}
            QMenu::separator{height:1px;background:#dcc;margin:4px 12px;}
        """)

        # 按 README 行号顺序排列
        a_idle   = QAction("🐹 待机",      m)   # row 0
        a_rr     = QAction("➡🐹 向右跑",   m)   # row 1
        a_rl     = QAction("⬅🐹 向左跑",   m)   # row 2
        a_waving = QAction("🖐️ 摸摸",      m)   # row 3
        a_jump   = QAction("🍊 跳跃",      m)   # row 4
        a_fail   = QAction("😵 失败",      m)   # row 5
        a_wait   = QAction("♨️ 等待",      m)   # row 6
        a_run    = QAction("🏃 奔跑",      m)   # row 7
        a_review = QAction("🤔 审核",      m)   # row 8
        a_exit   = QAction("❌ 退出",      m)

        a_idle.triggered.connect(lambda: self.set_state("idle"))
        a_rr.triggered.connect(lambda: self.set_state("running_right", 8000))
        a_rl.triggered.connect(lambda: self.set_state("running_left", 8000))
        a_waving.triggered.connect(lambda: self.set_state("waving", 3500))
        a_jump.triggered.connect(lambda: self.set_state("jumping", 5000))
        a_fail.triggered.connect(lambda: self.set_state("failed", 4000))
        a_wait.triggered.connect(lambda: self.set_state("waiting", 10000))
        a_run.triggered.connect(lambda: self.set_state("running", 5000))
        a_review.triggered.connect(lambda: self.set_state("review", 5000))
        a_exit.triggered.connect(QApplication.quit)

        m.addActions([a_idle, a_rr, a_rl, a_waving, a_jump,
                       a_fail, a_wait, a_run, a_review])
        m.addSeparator()
        m.addAction(a_exit)

        m.exec_(event.globalPos())


# ═══════════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("卡皮巴拉桌面宠物")
    pet = CapybaraPet()
    pet.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()


# ═══════════════════════════════════════════════════════════════
#  打包
# ═══════════════════════════════════════════════════════════════
# Windows:
#   pyinstaller --onefile --noconsole --add-data "assets;assets" --name CapybaraPet lulu_pet.py
# macOS:
#   pyinstaller --onefile --noconsole --add-data "assets:assets" --name CapybaraPet lulu_pet.py
