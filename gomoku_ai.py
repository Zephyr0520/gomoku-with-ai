"""
五子棋 AI 引擎 — 强对抗 Minimax + Alpha-Beta 剪枝

Key fixes over v1:
  - _count_through() — counts stones in BOTH directions from a position.
    This fixes find_winning_move / _move_score which previously only
    looked forward and therefore missed threats on the "backward" side.
  - Smarter candidate-generation (distance=1, always faster & sufficient).
  - Stronger defense-weighting in move-ordering heuristic.
  - find_winning_move now only scans candidates, not all 225 cells.
  - full-board eval restricted to cells near stones for speed.
  - Time management: early moves get 0.8 s, mid-game gets 3.5 s.
  - Fixed minimax terminal-node win-checks — they used to rely on the
    same broken find_winning_move.
"""

import time
from typing import List, Tuple, Optional

# ── Constants ────────────────────────────────────────────────────────────
SIZE = 15
EMPTY, BLACK, WHITE = 0, 1, 2
DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)]

# (consecutive_stones, open_ends) → score
PATTERN = {
    (5, 0): 100_000_000, (5, 1): 100_000_000, (5, 2): 100_000_000,
    (4, 2):  15_000_000,                              # open four
    (4, 1):   1_500_000,                              # blocked four
    (3, 2):     500_000,                              # open three
    (3, 1):      50_000,                              # blocked three
    (2, 2):       3_000,                              # open two
    (2, 1):         300,                              # blocked two
    (1, 2):          50,                              # open one
    (1, 1):           5,
}


class TimeoutError(Exception):
    """Raised when the search runs out of time."""
    pass


# ═══════════════════════════════════════════════════════════════════════════
class GomokuAI:
    def __init__(self, size: int = SIZE):
        self.size = size

    # ──  candidate generation  ─────────────────────────────────────────

    def candidates(self, board: List[List[int]],
                   radius: int = 1) -> List[Tuple[int, int]]:
        """Return all empty cells within *radius* of any existing stone."""
        cand: set = set()
        has = False
        for r in range(self.size):
            for c in range(self.size):
                if board[r][c] == EMPTY:
                    continue
                has = True
                r0, r1 = max(0, r - radius), min(self.size - 1, r + radius)
                c0, c1 = max(0, c - radius), min(self.size - 1, c + radius)
                for nr in range(r0, r1 + 1):
                    for nc in range(c0, c1 + 1):
                        if board[nr][nc] == EMPTY:
                            cand.add((nr, nc))
        if not has:
            return [(self.size // 2, self.size // 2)]       # first move
        return list(cand)

    # ──  pattern helpers  ──────────────────────────────────────────────

    def _count_through(self, board: List[List[int]],
                       r: int, c: int, dr: int, dc: int,
                       player: int) -> Tuple[int, int]:
        """Count consecutive *player* stones passing through (r,c)
        in BOTH directions along (dr,dc).  Returns (count, open_ends).

        This is the FIXED version — v1 only looked forward."""
        count = 1          # (r, c) itself (must already be *player*)
        opens = 0

        # ── forward ──
        rr, cc = r + dr, c + dc
        while 0 <= rr < self.size and 0 <= cc < self.size:
            if board[rr][cc] != player:
                if board[rr][cc] == EMPTY:
                    opens += 1
                break
            count += 1
            rr += dr
            cc += dc

        # ── backward ──
        rr, cc = r - dr, c - dc
        while 0 <= rr < self.size and 0 <= cc < self.size:
            if board[rr][cc] != player:
                if board[rr][cc] == EMPTY:
                    opens += 1
                break
            count += 1
            rr -= dr
            cc -= dc

        return count, opens

    # ──  full-board evaluation  ────────────────────────────────────────

    def evaluate(self, board: List[List[int]], player: int) -> int:
        """Evaluate the board from *player*'s perspective.

        Only scans cells near stones to save time."""
        opp = WHITE if player == BLACK else BLACK
        score = 0

        # Build a set of all cells that are either occupied or adjacent
        active: set = set()
        for r in range(self.size):
            for c in range(self.size):
                if board[r][c] != EMPTY:
                    for dr in range(-1, 2):
                        for dc in range(-1, 2):
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < self.size and 0 <= nc < self.size:
                                active.add((nr, nc))

        for r, c in active:
            stone = board[r][c]
            if stone == EMPTY:
                continue
            for dr, dc in DIRECTIONS:
                # only evaluate from pattern-start (prevent double-count)
                pr, pc = r - dr, c - dc
                if (0 <= pr < self.size and 0 <= pc < self.size
                        and board[pr][pc] == stone):
                    continue
                cnt, ends = self._count_through(board, r, c, dr, dc, stone)
                if cnt >= 5:
                    return 100_000_000 if stone == player else -100_000_000
                ps = PATTERN.get((cnt, ends), 0)
                if stone == player:
                    score += ps
                else:
                    score -= ps * 11 // 10
        return score

    # ──  immediate-win detection  ──────────────────────────────────────

    def find_winning_move(self, board: List[List[int]],
                          player: int) -> Optional[Tuple[int, int]]:
        """Return a one-move win for *player*, or None.

        Only checks candidate cells (near existing stones)."""
        for r, c in self.candidates(board, 1):
            if board[r][c] != EMPTY:
                continue
            board[r][c] = player
            for dr, dc in DIRECTIONS:
                cnt, _ = self._count_through(board, r, c, dr, dc, player)
                if cnt >= 5:
                    board[r][c] = EMPTY
                    return (r, c)
            board[r][c] = EMPTY
        return None

    # ──  move-ordering heuristic  ──────────────────────────────────────

    def _move_heuristic(self, board: List[List[int]],
                        r: int, c: int, player: int) -> int:
        """Heuristic score for placing *player* at (r,c).

        Returns a huge value for a winning or must-block move."""
        score = 0
        opp = WHITE if player == BLACK else BLACK

        # ── offensive patterns ──
        board[r][c] = player
        for dr, dc in DIRECTIONS:
            cnt, ends = self._count_through(board, r, c, dr, dc, player)
            if cnt >= 5:
                board[r][c] = EMPTY
                return 100_000_000
            score += PATTERN.get((cnt, ends), 0)
        board[r][c] = EMPTY

        # ── defensive patterns ──
        board[r][c] = opp
        best_def = 0
        for dr, dc in DIRECTIONS:
            cnt, ends = self._count_through(board, r, c, dr, dc, opp)
            if cnt >= 5:
                board[r][c] = EMPTY
                return 99_999_999                              # must-block
            p = PATTERN.get((cnt, ends), 0)
            if p > best_def:
                best_def = p
            score += p * 12 // 10                              # 1.2× defense
        board[r][c] = EMPTY

        # if best defense ≥ open-three level, boost heavily
        if best_def >= 500_000:
            score += best_def

        # centre-bias (mild)
        center = self.size // 2
        score += max(0, 120 - (abs(r - center) + abs(c - center)) * 15)

        return score

    def order_moves(self, board: List[List[int]],
                    moves: List[Tuple[int, int]],
                    player: int) -> List[Tuple[int, int]]:
        scored = [(self._move_heuristic(board, r, c, player), r, c)
                  for r, c in moves]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [(r, c) for _, r, c in scored]

    # ──  terminal detection  ─────────────────────────────────────────

    def _board_winner(self, board: List[List[int]]) -> Optional[int]:
        """Return the colour that already has 5-in-a-row on the board,
        or None.  Only checks from pattern-starts to avoid double work."""
        for r in range(self.size):
            for c in range(self.size):
                stone = board[r][c]
                if stone == EMPTY:
                    continue
                for dr, dc in DIRECTIONS:
                    pr, pc = r - dr, c - dc
                    if (0 <= pr < self.size and 0 <= pc < self.size
                            and board[pr][pc] == stone):
                        continue
                    cnt, _ = self._count_through(board, r, c, dr, dc, stone)
                    if cnt >= 5:
                        return stone
        return None

    # ──  minimax  ─────────────────────────────────────────────────────

    def minimax(self, board: List[List[int]],
                depth: int, alpha: int, beta: int,
                maximizing: bool, player: int, ai_player: int,
                start_t: float, deadline: float) -> int:

        if time.time() - start_t >= deadline:
            raise TimeoutError()

        opp = WHITE if player == BLACK else BLACK

        # ── terminal: board already has a winner  ──
        winner = self._board_winner(board)
        if winner == ai_player:
            return 100_000_000 - (10 - depth)
        elif winner is not None:
            return -100_000_000 + (10 - depth)

        # ── can the CURRENT player win in one move?  ──
        if self.find_winning_move(board, player):
            return (100_000_000 - (10 - depth)) if maximizing \
                   else (-100_000_000 + (10 - depth))

        if depth == 0:
            return self.evaluate(board, ai_player)

        moves = self.candidates(board, 1)
        if not moves:
            return 0

        moves = self.order_moves(board, moves, player)
        moves = moves[:12]          # search-width limit

        if maximizing:
            value = -10**18
            for r, c in moves:
                board[r][c] = player
                try:
                    v = self.minimax(board, depth - 1, alpha, beta, False,
                                     opp, ai_player, start_t, deadline)
                finally:
                    board[r][c] = EMPTY
                if v > value:
                    value = v
                if value > alpha:
                    alpha = value
                if beta <= alpha:
                    break
            return value
        else:
            value = 10**18
            for r, c in moves:
                board[r][c] = player
                try:
                    v = self.minimax(board, depth - 1, alpha, beta, True,
                                     opp, ai_player, start_t, deadline)
                finally:
                    board[r][c] = EMPTY
                if v < value:
                    value = v
                if value < beta:
                    beta = value
                if beta <= alpha:
                    break
            return value

    # ──  public API  ──────────────────────────────────────────────────

    def get_best_move(self, board: List[List[int]],
                      player: int,
                      time_limit: float = 3.5) -> Tuple[int, int]:
        """Return the best move for *player*.

        Time management:
          - opening (≤4 stones):        0.6 s — nearly instant
          - early game (5–12 stones):   1.5 s
          - mid game (13+ stones):      3.5 s
        """

        # ── count stones ──
        stone_cnt = sum(1 for r in range(self.size) for c in range(self.size)
                        if board[r][c] != EMPTY)

        # first move
        if stone_cnt == 0:
            return (self.size // 2, self.size // 2)

        # second move as white — stay near opponent's first stone
        if stone_cnt == 1 and player == WHITE:
            for r in range(self.size):
                for c in range(self.size):
                    if board[r][c] == BLACK:
                        for dr in (-1, 0, 1):
                            for dc in (-1, 0, 1):
                                nr, nc = r + dr, c + dc
                                if (0 <= nr < self.size and 0 <= nc < self.size
                                        and board[nr][nc] == EMPTY):
                                    return (nr, nc)

        # adjust time-limit based on game phase
        if stone_cnt <= 4:
            time_limit = 0.6
        elif stone_cnt <= 12:
            time_limit = 1.5

        opp = WHITE if player == BLACK else BLACK

        # ── immediate win  ──
        win = self.find_winning_move(board, player)
        if win:
            return win

        # ── must-block  ──
        block = self.find_winning_move(board, opp)
        if block:
            # also check: is there a forced double-threat response?
            # For safety always block.
            return block

        # ── candidate moves ──
        moves = self.candidates(board, 1)
        if len(moves) <= 1:
            return moves[0] if moves else (self.size // 2, self.size // 2)

        moves = self.order_moves(board, moves, player)
        best_move = moves[0]
        start = time.time()

        # ── iterative deepening ──
        try:
            for depth in range(2, 16, 2):
                best_at_depth = None
                best_val = -10**18
                alpha = -10**18
                beta = 10**18

                search_moves = moves[:15]
                for r, c in search_moves:
                    board[r][c] = player
                    try:
                        v = self.minimax(board, depth - 1, alpha, beta, False,
                                         opp, player, start, time_limit - 0.15)
                    finally:
                        board[r][c] = EMPTY

                    if v > best_val:
                        best_val = v
                        best_at_depth = (r, c)
                    if v > alpha:
                        alpha = v
                    if beta <= alpha:
                        break

                if best_at_depth:
                    best_move = best_at_depth

                if best_val >= 99_999_990:
                    break

        except TimeoutError:
            pass

        return best_move
