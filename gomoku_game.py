#!/usr/bin/env python3
"""
五子棋  ——  精美 Pygame 界面
Gomoku — Beautiful Pygame-based game with PvP & PvAI modes.

Features:
  - 15×15 board with wood-grain texture and 3D stones
  - Player vs Player  /  Player vs AI
  - Choose Black or White stones
  - Last-move indicator & winning-line highlight
  - New Game / Undo
  - Strong AI with deep iterative-deepening search
"""

import sys
import os
import threading
import time
import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gomoku_ai import GomokuAI, SIZE, EMPTY, BLACK, WHITE, DIRECTIONS
from gomoku_ai2 import GomokuAI2

# ═══════════════════════════════════════════════════════════════════════
#  Translations
# ═══════════════════════════════════════════════════════════════════════

T = {
    "zh": {
        "title": "五子棋",
        "title_menu": "五 子 棋",
        "subtitle": "Gomoku",
        "new_game": "新游戏",
        "undo": "悔棋",
        "black_stone": "黑棋 ●",
        "white_stone": "白棋 ○",
        "black_wins": "黑棋 胜！",
        "white_wins": "白棋 胜！",
        "draw": "平局！",
        "thinking": "思考中...",
        "mode_pvp": "人人对战",
        "mode_pve": "人机对战",
        "mode_aie": "AI 对战",
        "mode_label": "模式: {}",
        "move_count": "第 {} 手",
        "you_black": "执黑",
        "you_white": "执白",
        "player_label": "玩家: {}",
        "ai_version": "AI 版本: {}",
        "black_ai": "黑棋: AI {}",
        "white_ai": "白棋: AI {}",
        "choose_color": "选择您的棋子颜色",
        "choose_ai": "选择 AI 版本",
        "black_ai_label": "黑棋 AI",
        "white_ai_label": "白棋 AI",
        "play_black": "● 执黑",
        "play_white": "○ 执白",
        "start_game": "开 始 游 戏",
        "lang_label": "语言 Language",
        "window_title": "五子棋  —  Gomoku",
    },
    "en": {
        "title": "Gomoku",
        "title_menu": "G O M O K U",
        "subtitle": "五子棋",
        "new_game": "New Game",
        "undo": "Undo",
        "black_stone": "Black ●",
        "white_stone": "White ○",
        "black_wins": "Black Wins!",
        "white_wins": "White Wins!",
        "draw": "Draw!",
        "thinking": "Thinking...",
        "mode_pvp": "PvP",
        "mode_pve": "PvAI",
        "mode_aie": "AI vs AI",
        "mode_label": "Mode: {}",
        "move_count": "Move {}",
        "you_black": "Black",
        "you_white": "White",
        "player_label": "You: {}",
        "ai_version": "AI Version: {}",
        "black_ai": "Black: AI {}",
        "white_ai": "White: AI {}",
        "choose_color": "Choose Your Color",
        "choose_ai": "Select AI Version",
        "black_ai_label": "Black AI",
        "white_ai_label": "White AI",
        "play_black": "● Black",
        "play_white": "○ White",
        "start_game": "Start Game",
        "lang_label": "语言 Language",
        "window_title": "Gomoku  —  五子棋",
    },
}

# ═══════════════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════════════

CELL = 36
MARGIN = 30
BOARD_PX = (SIZE - 1) * CELL                     # 504 px grid span
BOARD_TOTAL = BOARD_PX + 2 * MARGIN               # 564 px with padding
BOARD_Y = 40
SIDEBAR_X = BOARD_TOTAL + 12
SIDEBAR_W = 190
WINDOW_W = SIDEBAR_X + SIDEBAR_W + 16
WINDOW_H = BOARD_TOTAL + 56

# colours
WOOD       = (222, 184, 135)
GRID       = (50, 35, 20)
SIDEBAR_BG = (250, 244, 236)
TEXT       = (50, 40, 30)
BTN        = (170, 130, 85)
BTN_HVR    = (200, 160, 110)
BTN_DIS    = (160, 150, 140)
MARK       = (255, 60, 60)
WIN_GLOW   = (255, 215, 0)

# star-point positions for a 15×15 board
STAR_PTS = [(3, 3), (3, 7), (3, 11),
            (7, 3), (7, 7), (7, 11),
            (11, 3), (11, 7), (11, 11)]


# ═══════════════════════════════════════════════════════════════════════
#  Simple Button
# ═══════════════════════════════════════════════════════════════════════

class Button:
    def __init__(self, rect, text, cb, font, enabled=True):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.cb = cb
        self.font = font
        self.enabled = enabled
        self.hovered = False

    def draw(self, screen):
        if not self.enabled:
            c = BTN_DIS
        elif self.hovered:
            c = BTN_HVR
        else:
            c = BTN
        pygame.draw.rect(screen, c, self.rect, border_radius=6)
        pygame.draw.rect(screen, (100, 80, 50), self.rect, 1, border_radius=6)
        col = (255, 255, 255) if self.enabled else (200, 200, 200)
        txt = self.font.render(self.text, True, col)
        r = txt.get_rect(center=self.rect.center)
        screen.blit(txt, r)

    def handle(self, ev):
        if not self.enabled:
            return
        if ev.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and self.hovered:
            self.cb()


# ═══════════════════════════════════════════════════════════════════════
#  Game
# ═══════════════════════════════════════════════════════════════════════

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self.lang = "zh"
        pygame.display.set_caption(self.t("window_title"))
        self.clock = pygame.time.Clock()
        self.fonts = self._load_fonts()
        self._reset_state()
        self._build_surfaces()
        self._build_buttons()

    # ── fonts ──────────────────────────────────────────────────────────
    def _load_fonts(self):
        """Try a CJK-capable system font; fall back to default."""
        candidates = [
            "Microsoft YaHei", "SimHei", "SimSun",
            "WenQuanYi Micro Hei", "Noto Sans CJK SC",
            "Droid Sans Fallback",
        ]
        found = None
        for name in candidates:
            try:
                f = pygame.font.SysFont(name, 20)
                if f.render("测", True, (0, 0, 0)).get_width() > 0:
                    found = name
                    break
            except Exception:
                continue
        if found:
            return dict(
                title=pygame.font.SysFont(found, 36),
                subtitle=pygame.font.SysFont(found, 18),
                body=pygame.font.SysFont(found, 22),
                small=pygame.font.SysFont(found, 16),
                btn=pygame.font.SysFont(found, 21),
                huge=pygame.font.SysFont(found, 48),
            )
        return dict(
            title=pygame.font.Font(None, 48),
            subtitle=pygame.font.Font(None, 24),
            body=pygame.font.Font(None, 28),
            small=pygame.font.Font(None, 22),
            btn=pygame.font.Font(None, 26),
            huge=pygame.font.Font(None, 60),
        )

    # ── state ──────────────────────────────────────────────────────────
    def _reset_state(self):
        self.board = [[EMPTY] * SIZE for _ in range(SIZE)]
        self.history = []                   # (r, c, player)
        self.turn = BLACK
        self.last_move = None
        self.over = False
        self.winner = None
        self.win_stones = []                # stones to highlight

        self.mode = None                    # None | 'pvp' | 'pve' | 'aie'
        self.human_color = BLACK
        self.ai_color = WHITE
        self.ai = None
        self.ai_black = None
        self.ai_white = None
        self.ai_move = None
        self.ai_busy = False
        self.ai_delay = -1                   # -1 = not yet started; 0 = ready to trigger

        self.show_menu = True
        self.menu_mode = None
        self.menu_color = BLACK
        self.ai_version = 1            # 1 = AI 1,  2 = AI 2
        self.ai_black_version = 1      # AI-vs-AI: black's AI
        self.ai_white_version = 1      # AI-vs-AI: white's AI

    # ── i18n ───────────────────────────────────────────────────────────
    def t(self, key: str, *args) -> str:
        """Look up translated string, optionally formatting with args."""
        s = T[self.lang].get(key, key)
        if args:
            s = s.format(*args)
        return s

    def _cmd_lang(self):
        """Toggle language."""
        self.lang = "en" if self.lang == "zh" else "zh"
        pygame.display.set_caption(self.t("window_title"))
        self._build_buttons()

    def _build_surfaces(self):
        """Pre-render static graphics."""
        bw = BOARD_PX + 2 * MARGIN
        bh = BOARD_PX + 2 * MARGIN
        self.bg = pygame.Surface((bw, bh))
        self.bg.fill(WOOD)
        # subtle grain
        for y in range(0, bh, 3):
            h = hash(str(y + 123)) % 17 - 8
            r = max(0, min(255, WOOD[0] + h))
            g = max(0, min(255, WOOD[1] + h))
            b_ = max(0, min(255, WOOD[2] + h))
            pygame.draw.line(self.bg, (r, g, b_), (0, y), (bw, y))
        # board border
        pygame.draw.rect(self.bg, (120, 80, 40), (0, 0, bw, bh), 3)

        # ── stones ──
        rad = CELL // 2 - 2
        d = rad * 2
        cx = cy = d // 2

        def make_stone(layers, highlight_pos, highlight_c, border_c):
            s = pygame.Surface((d, d), pygame.SRCALPHA)
            for i, col in layers:
                pygame.draw.circle(s, col, (cx, cy), i)
            # highlight
            hx, hy = highlight_pos
            pygame.draw.circle(s, highlight_c, (cx + hx, cy + hy), max(3, rad // 3))
            # border
            pygame.draw.circle(s, border_c, (cx, cy), rad, 1)
            return s

        # black
        black_layers = [
            (rad, (25, 25, 25)),
            (rad - 2, (40, 40, 40)),
        ]
        self.black_surf = make_stone(black_layers, (-3, -3), (140, 140, 140), (0, 0, 0))

        # white
        white_layers = [
            (rad, (200, 200, 200)),
            (rad - 2, (230, 230, 230)),
        ]
        self.white_surf = make_stone(white_layers, (-2, -2), (255, 255, 255), (100, 100, 100))

        # ── sidebar bg ──
        self.sidebar_surf = pygame.Surface((SIDEBAR_W, WINDOW_H))
        self.sidebar_surf.fill(SIDEBAR_BG)

    def _build_buttons(self):
        self.btns = []
        bw = SIDEBAR_W - 30
        x = SIDEBAR_X + 15

        self.btn_new = Button((x, 340, bw, 40), self.t("new_game"), self._cmd_new,
                              self.fonts['btn'])
        self.btn_undo = Button((x, 390, bw, 40), self.t("undo"), self._cmd_undo,
                               self.fonts['btn'])
        self.btns = [self.btn_new, self.btn_undo]

    # ── coord helpers ──────────────────────────────────────────────────
    def _b2s(self, r, c):
        return (MARGIN + c * CELL, BOARD_Y + r * CELL)

    def _s2b(self, x, y):
        c = round((x - MARGIN) / CELL)
        r = round((y - BOARD_Y) / CELL)
        if 0 <= r < SIZE and 0 <= c < SIZE:
            sx, sy = self._b2s(r, c)
            if abs(x - sx) <= CELL // 2 and abs(y - sy) <= CELL // 2:
                return (r, c)
        return None

    # ── board logic ────────────────────────────────────────────────────
    def _check_win(self, r: int, c: int):
        """Return (won, [stone_list]) for the last-placed stone."""
        player = self.board[r][c]
        for dr, dc in DIRECTIONS:
            line = [(r, c)]
            # forward
            rr, cc = r + dr, c + dc
            while 0 <= rr < SIZE and 0 <= cc < SIZE and self.board[rr][cc] == player:
                line.append((rr, cc))
                rr += dr
                cc += dc
            # backward
            rr, cc = r - dr, c - dc
            while 0 <= rr < SIZE and 0 <= cc < SIZE and self.board[rr][cc] == player:
                line.append((rr, cc))
                rr -= dr
                cc -= dc
            if len(line) >= 5:
                return True, line
        return False, []

    def _is_draw(self):
        return all(self.board[r][c] != EMPTY for r in range(SIZE) for c in range(SIZE))

    def play(self, r: int, c: int) -> bool:
        """Place a stone at (r,c) for the current player."""
        if not (0 <= r < SIZE and 0 <= c < SIZE):
            return False
        if self.board[r][c] != EMPTY or self.over:
            return False

        self.board[r][c] = self.turn
        self.history.append((r, c, self.turn))
        self.last_move = (r, c)

        won, stones = self._check_win(r, c)
        if won:
            self.over = True
            self.winner = self.turn
            self.win_stones = stones
            return True

        if self._is_draw():
            self.over = True
            self.winner = None
            return True

        self.turn = WHITE if self.turn == BLACK else BLACK
        return True

    def _cmd_undo(self):
        if self.over or self.ai_busy or self.mode == 'aie':
            return
        if self.mode == 'pvp':
            if not self.history:
                return
            r, c, _ = self.history.pop()
            self.board[r][c] = EMPTY
            self.turn = WHITE if self.turn == BLACK else BLACK
        else:   # pve
            if self.turn != self.human_color:
                return
            n = 2 if len(self.history) >= 2 else 1
            for _ in range(n):
                r, c, _ = self.history.pop()
                self.board[r][c] = EMPTY
            self.turn = self.human_color
        self.last_move = self.history[-1][:2] if self.history else None
        self.over = False
        self.winner = None
        self.win_stones = []

    def _cmd_new(self):
        self._reset_state()
        self._build_buttons()

    # ── AI ─────────────────────────────────────────────────────────────
    def _start_ai(self):
        if self.ai_busy or self.over:
            return
        if self.mode == 'pve':
            if self.turn != self.ai_color:
                return
        elif self.mode != 'aie':
            return

        # Ensure AI instances exist
        if self.mode == 'pve' and self.ai is None:
            self.ai = GomokuAI() if self.ai_version == 1 else GomokuAI2()
        elif self.mode == 'aie':
            if self.ai_black is None:
                self.ai_black = GomokuAI() if self.ai_black_version == 1 else GomokuAI2()
            if self.ai_white is None:
                self.ai_white = GomokuAI() if self.ai_white_version == 1 else GomokuAI2()

        self.ai_busy = True
        self.ai_move = None
        who = self.turn                     # capture before threading

        # Pick the right AI instance
        if self.mode == 'aie':
            ai_instance = self.ai_black if who == BLACK else self.ai_white
        else:
            ai_instance = self.ai

        t = threading.Thread(target=lambda: self._ai_worker(who, ai_instance), daemon=True)
        t.start()

    def _ai_worker(self, for_player: int, ai_instance):
        board_copy = [row[:] for row in self.board]
        try:
            move = ai_instance.get_best_move(board_copy, for_player, time_limit=4.5)
            self.ai_move = move
        except Exception:
            self.ai_move = None

    # ── main loop helpers ───────────────────────────────────────────────
    def _update(self):
        # ── apply AI result when ready ──
        if self.ai_busy and self.ai_move is not None:
            r, c = self.ai_move
            self.play(r, c)
            self.ai_busy = False
            self.ai_move = None
            if self.mode == 'aie' and not self.over:
                self.ai_delay = 30                # ~1 s pause at 30 fps

        # ── AI-vs-AI auto-play ──
        if self.mode == 'aie' and not self.over and not self.ai_busy:
            if self.ai_delay > 0:
                self.ai_delay -= 1
            elif self.ai_delay == 0:
                self.ai_delay = -1                # prevent re-trigger
                self._start_ai()

    # ── drawing ─────────────────────────────────────────────────────────
    def _draw(self):
        self.screen.fill((240, 235, 225))

        # ── board ──
        self.screen.blit(self.bg, (0, BOARD_Y - MARGIN))
        gx, gy = MARGIN, BOARD_Y

        # grid lines
        for i in range(SIZE):
            x = gx + i * CELL
            pygame.draw.line(self.screen, GRID, (x, gy), (x, gy + BOARD_PX), 1)
            y = gy + i * CELL
            pygame.draw.line(self.screen, GRID, (gx, y), (gx + BOARD_PX, y), 1)

        # star points
        sr = 4
        for r, c in STAR_PTS:
            sx, sy = self._b2s(r, c)
            pygame.draw.circle(self.screen, GRID, (sx, sy), sr)

        # stones
        for r in range(SIZE):
            for c in range(SIZE):
                if self.board[r][c] == EMPTY:
                    continue
                surf = self.black_surf if self.board[r][c] == BLACK else self.white_surf
                sx, sy = self._b2s(r, c)
                self.screen.blit(surf, surf.get_rect(center=(sx, sy)))

        # last-move marker
        if self.last_move:
            lx, ly = self._b2s(*self.last_move)
            pygame.draw.circle(self.screen, MARK, (lx, ly), 5)

        # winning-line glow
        if self.win_stones:
            for r, c in self.win_stones:
                sx, sy = self._b2s(r, c)
                pygame.draw.circle(self.screen, WIN_GLOW, (sx, sy),
                                   CELL // 2 - 1, 3)

        # hover preview (human-turn modes only)
        if (not self.show_menu and not self.over and not self.ai_busy
                and self.mode != 'aie'):
            mouse = pygame.mouse.get_pos()
            rc = self._s2b(*mouse)
            if rc and self.board[rc[0]][rc[1]] == EMPTY:
                if (self.mode == 'pvp' or self.turn == self.human_color):
                    hx, hy = self._b2s(*rc)
                    col = (60, 60, 60, 100) if self.turn == BLACK else (255, 255, 255, 100)
                    s = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
                    pygame.draw.circle(s, col, (CELL // 2, CELL // 2), CELL // 2 - 2)
                    self.screen.blit(s, (hx - CELL // 2, hy - CELL // 2))

        # ── sidebar ──
        self.screen.blit(self.sidebar_surf, (SIDEBAR_X, 0))
        pygame.draw.line(self.screen, (200, 190, 180),
                         (SIDEBAR_X, 0), (SIDEBAR_X, WINDOW_H), 1)

        # sidebar text
        f = self.fonts
        x = SIDEBAR_X + 15

        title = f['title'].render(self.t("title"), True, TEXT)
        self.screen.blit(title, (x, 30))

        # turn indicator
        turn_y = 90
        if self.over:
            if self.winner is None:
                msg = self.t("draw")
            else:
                name = self.t("black_wins") if self.winner == BLACK else self.t("white_wins")
                msg = name
            txt = f['body'].render(msg, True, (200, 40, 40))
        elif self.ai_busy:
            txt = f['body'].render(self.t("thinking"), True, (180, 120, 60))
        else:
            pname = self.t("black_stone") if self.turn == BLACK else self.t("white_stone")
            txt = f['body'].render(pname, True, TEXT)
        self.screen.blit(txt, (x, turn_y))

        # mode
        mode_y = 135
        mode_map = {"pvp": self.t("mode_pvp"), "pve": self.t("mode_pve"), "aie": self.t("mode_aie")}
        mode_str = mode_map.get(self.mode, "")
        if mode_str:
            mt = f['small'].render(self.t("mode_label", mode_str), True, (140, 130, 120))
            self.screen.blit(mt, (x, mode_y))

        # move count
        mc_y = 165
        ct = f['small'].render(self.t("move_count", len(self.history)), True, (140, 130, 120))
        self.screen.blit(ct, (x, mc_y))

        # color info for PvE
        if self.mode == 'pve' and not self.show_menu:
            cy_ = 195
            you = self.t("you_black") if self.human_color == BLACK else self.t("you_white")
            you_t = f['small'].render(self.t("player_label", you), True, (140, 130, 120))
            self.screen.blit(you_t, (x, cy_))

            cy2_ = 222
            ai_ver = self.t("ai_version", self.ai_version)
            ai_t = f['small'].render(ai_ver, True, (140, 130, 120))
            self.screen.blit(ai_t, (x, cy2_))

        # AI version info for AI-vs-AI
        if self.mode == 'aie' and not self.show_menu:
            av_y = 195
            bv = self.t("black_ai", self.ai_black_version)
            wv = self.t("white_ai", self.ai_white_version)
            bv_t = f['small'].render(bv, True, (140, 130, 120))
            wv_t = f['small'].render(wv, True, (140, 130, 120))
            self.screen.blit(bv_t, (x, av_y))
            self.screen.blit(wv_t, (x, av_y + 24))

        # buttons
        self.btn_undo.enabled = (not self.over and len(self.history) > 0
                                 and not self.ai_busy and self.mode != 'aie')
        for b in self.btns:
            b.draw(self.screen)

        # ── menu overlay ──
        if self.show_menu:
            self._draw_menu()

    def _draw_menu(self):
        ov = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        self.screen.blit(ov, (0, 0))

        pw, ph = 380, 540                      # taller panel for AI selectors
        cx, cy = WINDOW_W // 2, WINDOW_H // 2 - 20
        px, py = cx - pw // 2, cy - ph // 2

        # panel
        pygame.draw.rect(self.screen, (248, 243, 234),
                         (px, py, pw, ph), border_radius=14)
        pygame.draw.rect(self.screen, (180, 140, 100),
                         (px, py, pw, ph), 2, border_radius=14)

        f = self.fonts

        # title
        t = f['huge'].render(self.t("title_menu"), True, TEXT)
        self.screen.blit(t, (cx - t.get_width() // 2, py + 24))
        st = f['subtitle'].render(self.t("subtitle"), True, (150, 130, 110))
        self.screen.blit(st, (cx - st.get_width() // 2, py + 72))

        # ── language toggle (top-right of panel) ──
        lang_btn_w, lang_btn_h = 120, 26
        self._menu_lang_r = pygame.Rect(px + pw - lang_btn_w - 10, py + 10, lang_btn_w, lang_btn_h)
        lc = BTN_HVR if self._menu_lang_r.collidepoint(pygame.mouse.get_pos()) else BTN
        pygame.draw.rect(self.screen, lc, self._menu_lang_r, border_radius=5)
        lt = f['small'].render(self.t("lang_label"), True, (255, 255, 255))
        self.screen.blit(lt, (self._menu_lang_r.centerx - lt.get_width() // 2,
                              self._menu_lang_r.centery - lt.get_height() // 2))

        # ── menu button helper ──
        def menu_btn(rect, label, selected):
            c = (170, 130, 85) if selected else (200, 190, 175)
            pygame.draw.rect(self.screen, c, rect, border_radius=7)
            if selected:
                pygame.draw.rect(self.screen, (120, 80, 40), rect, 2, border_radius=7)
            col = (255, 255, 255) if selected else (120, 110, 100)
            l = f['btn'].render(label, True, col)
            self.screen.blit(l, (rect.centerx - l.get_width() // 2,
                                 rect.centery - l.get_height() // 2))

        # ── three stacked mode buttons ──
        bw_, bh_ = 300, 42
        by = py + 115
        gap = 10
        pvp_r  = pygame.Rect(cx - bw_ // 2, by, bw_, bh_)
        pve_r  = pygame.Rect(cx - bw_ // 2, by + bh_ + gap, bw_, bh_)
        aie_r  = pygame.Rect(cx - bw_ // 2, by + 2 * (bh_ + gap), bw_, bh_)

        menu_btn(pvp_r, self.t("mode_pvp"), self.mode == 'pvp')
        menu_btn(pve_r, self.t("mode_pve"), self.mode == 'pve')
        menu_btn(aie_r, self.t("mode_aie"), self.mode == 'aie')

        # ── colour selection (only PvE) ──
        col_y = by + 3 * (bh_ + gap) + 20
        if self.mode == 'pve':
            lbl = f['small'].render(self.t("choose_color"), True, TEXT)
            self.screen.blit(lbl, (cx - lbl.get_width() // 2, col_y))

            cw, ch = 130, 42
            csp = (pw - 2 * cw) // 3
            b_r = pygame.Rect(px + csp, col_y + 32, cw, ch)
            w_r = pygame.Rect(px + pw - csp - cw, col_y + 32, cw, ch)
            menu_btn(b_r, self.t("play_black"), self.menu_color == BLACK)
            menu_btn(w_r, self.t("play_white"), self.menu_color == WHITE)
            self._menu_black_r = b_r
            self._menu_white_r = w_r
        else:
            self._menu_black_r = None
            self._menu_white_r = None

        # ── AI version selection ──
        aw, ah = 110, 36
        ai_gap = 20
        ai_y_base = col_y + 90 if self.mode == 'pve' else col_y + 20

        if self.mode == 'pve':
            # PvE: single AI selector
            ai_lbl = f['small'].render(self.t("choose_ai"), True, TEXT)
            self.screen.blit(ai_lbl, (cx - ai_lbl.get_width() // 2, ai_y_base))

            ai1_r = pygame.Rect(cx - aw - ai_gap // 2, ai_y_base + 30, aw, ah)
            ai2_r = pygame.Rect(cx + ai_gap // 2, ai_y_base + 30, aw, ah)
            menu_btn(ai1_r, "AI 1", self.ai_version == 1)
            menu_btn(ai2_r, "AI 2", self.ai_version == 2)
            self._menu_ai1_r = ai1_r
            self._menu_ai2_r = ai2_r
            self._menu_ai_black1_r = self._menu_ai_black2_r = None
            self._menu_ai_white1_r = self._menu_ai_white2_r = None

        elif self.mode == 'aie':
            # AI-vs-AI: two AI selectors (black + white)
            # ── Black AI ──
            blk_lbl = f['small'].render(self.t("black_ai_label"), True, TEXT)
            self.screen.blit(blk_lbl, (cx - blk_lbl.get_width() // 2, ai_y_base))

            blk1_r = pygame.Rect(cx - aw - ai_gap // 2, ai_y_base + 30, aw, ah)
            blk2_r = pygame.Rect(cx + ai_gap // 2, ai_y_base + 30, aw, ah)
            menu_btn(blk1_r, "AI 1", self.ai_black_version == 1)
            menu_btn(blk2_r, "AI 2", self.ai_black_version == 2)
            self._menu_ai_black1_r = blk1_r
            self._menu_ai_black2_r = blk2_r

            # ── White AI ──
            wht_y = ai_y_base + 80
            wht_lbl = f['small'].render(self.t("white_ai_label"), True, TEXT)
            self.screen.blit(wht_lbl, (cx - wht_lbl.get_width() // 2, wht_y))

            wht1_r = pygame.Rect(cx - aw - ai_gap // 2, wht_y + 30, aw, ah)
            wht2_r = pygame.Rect(cx + ai_gap // 2, wht_y + 30, aw, ah)
            menu_btn(wht1_r, "AI 1", self.ai_white_version == 1)
            menu_btn(wht2_r, "AI 2", self.ai_white_version == 2)
            self._menu_ai_white1_r = wht1_r
            self._menu_ai_white2_r = wht2_r

            self._menu_ai1_r = self._menu_ai2_r = None
        else:
            self._menu_ai1_r = self._menu_ai2_r = None
            self._menu_ai_black1_r = self._menu_ai_black2_r = None
            self._menu_ai_white1_r = self._menu_ai_white2_r = None

        # ── start button ──
        if self.mode:
            sr = pygame.Rect(px + 40, py + ph - 65, pw - 80, 44)
            hover = sr.collidepoint(pygame.mouse.get_pos())
            sc = BTN_HVR if hover else BTN
            pygame.draw.rect(self.screen, sc, sr, border_radius=8)
            pygame.draw.rect(self.screen, (100, 80, 50), sr, 1, border_radius=8)
            stxt = f['btn'].render(self.t("start_game"), True, (255, 255, 255))
            self.screen.blit(stxt, (sr.centerx - stxt.get_width() // 2,
                                    sr.centery - stxt.get_height() // 2))
            self._menu_start_rect = sr
        else:
            self._menu_start_rect = None

        # store rects for click handling
        self._menu_pvp_r  = pvp_r
        self._menu_pve_r  = pve_r
        self._menu_aie_r  = aie_r

    # ── event loop ─────────────────────────────────────────────────────
    def _handle(self, ev):
        if ev.type == pygame.QUIT:
            raise SystemExit

        if self.show_menu:
            self._menu_click(ev)
            return

        for b in self.btns:
            b.handle(ev)

        if ev.type == pygame.MOUSEBUTTONDOWN and not self.ai_busy and not self.over:
            if self.mode == 'aie':                      # no manual clicks in AI vs AI
                return
            rc = self._s2b(*ev.pos)
            if rc:
                r, c = rc
                if self.mode == 'pvp':
                    self.play(r, c)
                elif self.mode == 'pve' and self.turn == self.human_color:
                    if self.play(r, c):
                        self._start_ai()

    def _menu_click(self, ev):
        if ev.type != pygame.MOUSEBUTTONDOWN:
            return
        pos = ev.pos

        # language toggle (always active)
        if hasattr(self, '_menu_lang_r') and self._menu_lang_r.collidepoint(pos):
            self._cmd_lang()
            return

        # three mode buttons
        if hasattr(self, '_menu_pvp_r') and self._menu_pvp_r.collidepoint(pos):
            self.mode = 'pvp'
            self.menu_color = BLACK
            return
        if hasattr(self, '_menu_pve_r') and self._menu_pve_r.collidepoint(pos):
            self.mode = 'pve'
            return
        if hasattr(self, '_menu_aie_r') and self._menu_aie_r.collidepoint(pos):
            self.mode = 'aie'
            return

        # colour buttons (PvE)
        if self.mode == 'pve':
            if hasattr(self, '_menu_black_r') and self._menu_black_r and self._menu_black_r.collidepoint(pos):
                self.menu_color = BLACK
                return
            if hasattr(self, '_menu_white_r') and self._menu_white_r and self._menu_white_r.collidepoint(pos):
                self.menu_color = WHITE
                return

        # AI version buttons (PvE)
        if self.mode == 'pve':
            if hasattr(self, '_menu_ai1_r') and self._menu_ai1_r and self._menu_ai1_r.collidepoint(pos):
                self.ai_version = 1
                return
            if hasattr(self, '_menu_ai2_r') and self._menu_ai2_r and self._menu_ai2_r.collidepoint(pos):
                self.ai_version = 2
                return

        # AI version buttons (AI-vs-AI): black
        if self.mode == 'aie':
            if hasattr(self, '_menu_ai_black1_r') and self._menu_ai_black1_r and self._menu_ai_black1_r.collidepoint(pos):
                self.ai_black_version = 1
                return
            if hasattr(self, '_menu_ai_black2_r') and self._menu_ai_black2_r and self._menu_ai_black2_r.collidepoint(pos):
                self.ai_black_version = 2
                return
            # white
            if hasattr(self, '_menu_ai_white1_r') and self._menu_ai_white1_r and self._menu_ai_white1_r.collidepoint(pos):
                self.ai_white_version = 1
                return
            if hasattr(self, '_menu_ai_white2_r') and self._menu_ai_white2_r and self._menu_ai_white2_r.collidepoint(pos):
                self.ai_white_version = 2
                return

        # start button
        if self.mode and hasattr(self, '_menu_start_rect') and self._menu_start_rect:
            if self._menu_start_rect.collidepoint(pos):
                self.human_color = self.menu_color
                self.ai_color = WHITE if self.human_color == BLACK else BLACK

                def _make_ai(version: int) -> object:
                    return GomokuAI() if version == 1 else GomokuAI2()

                if self.mode == 'pve':
                    self.ai = _make_ai(self.ai_version)
                elif self.mode == 'aie':
                    self.ai_black = _make_ai(self.ai_black_version)
                    self.ai_white = _make_ai(self.ai_white_version)
                    self.ai = None   # not used in aie mode

                self.turn = BLACK
                self.show_menu = False
                # auto-start if AI plays first
                if self.mode == 'pve' and self.human_color == WHITE:
                    self._start_ai()
                elif self.mode == 'aie':
                    self._start_ai()         # AI-vs-AI: black AI starts immediately

    # ── run ────────────────────────────────────────────────────────────
    def run(self):
        try:
            while True:
                for ev in pygame.event.get():
                    self._handle(ev)
                self._update()
                self._draw()
                pygame.display.flip()
                self.clock.tick(30)
        except SystemExit:
            pass
        finally:
            pygame.quit()


# ═══════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    Game().run()
