"""
五子棋 AI 引擎 v2 — 增强评估 + Negamax Alpha-Beta

Improvements over AI 1:
  - Enhanced pattern evaluation: detects GAP patterns (X_XXX, XX_XX, etc.)
  - Killer-move heuristic: better move ordering
  - Quiescence search: avoids horizon effect at leaf nodes

Uses the same proven negamax + alpha-beta search structure as AI 1,
ensuring reliability while benefiting from the better evaluation function.
"""

import time
from typing import List, Tuple, Optional

# ── Constants ────────────────────────────────────────────────────────────
SIZE = 15
EMPTY, BLACK, WHITE = 0, 1, 2
DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)]

# (consecutive_stones, open_ends) → score  (same as AI 1)
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

# Gap patterns — AI 2 exclusive: (stones, gaps, open_ends) → score
GAP_PATTERN = {
    # Jump-four: 4 stones with 1 gap, both ends open → nearly unstoppable
    (4, 1, 2): 14_000_000,
    # Jump-four blocked one side
    (4, 1, 1):  1_200_000,
    # Jump-three: 3 stones with 1 gap, both ends open → strong threat
    (3, 1, 2):   400_000,
    # Jump-three blocked one side
    (3, 1, 1):    35_000,
    # Two stones with a gap, both ends open (setup)
    (2, 1, 2):     2_500,
}


class TimeoutError(Exception):
    """Raised when the search runs out of time."""
    pass


# ═══════════════════════════════════════════════════════════════════════════
class GomokuAI2:
    def __init__(self, size: int = SIZE):
        self.size = size
        self._killer: List[List[Optional[Tuple[int, int]]]] = []

    # ── candidate generation ──────────────────────────────────────────

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
            return [(self.size // 2, self.size // 2)]
        return list(cand)

    # ── pattern helpers ────────────────────────────────────────────────

    def _count_through(self, board: List[List[int]],
                       r: int, c: int, dr: int, dc: int,
                       player: int) -> Tuple[int, int]:
        """Count consecutive *player* stones passing through (r,c)
        in BOTH directions along (dr,dc).  Returns (count, open_ends)."""
        count = 1
        opens = 0

        # forward
        rr, cc = r + dr, c + dc
        while 0 <= rr < self.size and 0 <= cc < self.size:
            if board[rr][cc] != player:
                if board[rr][cc] == EMPTY:
                    opens += 1
                break
            count += 1
            rr += dr
            cc += dc

        # backward
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

    def _gap_score(self, board: List[List[int]],
                   r: int, c: int, dr: int, dc: int,
                   player: int) -> int:
        """Score gap patterns along (dr,dc) from (r,c) for *player*.

        Scans up to 9 cells forward from (r,c) and detects patterns
        like X_XXX, XX_XX, etc."""
        opp = WHITE if player == BLACK else BLACK
        cells = []

        rr, cc = r, c
        for _ in range(9):
            if not (0 <= rr < self.size and 0 <= cc < self.size):
                break
            cells.append(board[rr][cc])
            if board[rr][cc] == opp:
                break
            rr += dr
            cc += dc

        if len(cells) < 5:
            return 0

        best_score = 0
        for i in range(len(cells) - 4):
            window = cells[i:i + 5]
            if window[0] != player:
                continue

            stones = 0
            gaps = 0
            valid = True
            first_stone = -1
            last_stone = -1

            for j, v in enumerate(window):
                if v == player:
                    stones += 1
                    if first_stone == -1:
                        first_stone = j
                    last_stone = j
                elif v == opp:
                    valid = False
                    break

            if not valid or stones < 2:
                continue
            if stones >= 5:
                return 100_000_000

            for j in range(first_stone + 1, last_stone):
                if window[j] == EMPTY:
                    gaps += 1

            if gaps == 0:
                continue
            if gaps > 1:
                continue

            # Count open ends: cells just outside the window
            opens = 0
            if i > 0 and cells[i - 1] == EMPTY:
                opens += 1
            elif i == 0:
                pr, pc = r - dr, c - dc
                if 0 <= pr < self.size and 0 <= pc < self.size and board[pr][pc] == EMPTY:
                    opens += 1

            if i + 5 < len(cells) and cells[i + 5] == EMPTY:
                opens += 1
            elif i + 5 >= len(cells):
                last_rr = r + (i + 4) * dr
                last_cc = c + (i + 4) * dc
                nr, nc = last_rr + dr, last_cc + dc
                if 0 <= nr < self.size and 0 <= nc < self.size and board[nr][nc] == EMPTY:
                    opens += 1

            opens = min(opens, 2)
            score = GAP_PATTERN.get((stones, gaps, opens), 0)
            if score > best_score:
                best_score = score

        return best_score

    # ── full-board evaluation ──────────────────────────────────────────

    def evaluate(self, board: List[List[int]], player: int) -> int:
        """Evaluate the board from *player*'s perspective."""
        opp = WHITE if player == BLACK else BLACK
        score = 0

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

                # Gap pattern evaluation
                if cnt < 5:
                    gs = self._gap_score(board, r, c, dr, dc, stone)
                    if gs > 0:
                        if stone == player:
                            score += gs
                        else:
                            score -= gs * 11 // 10

        return score

    # ── immediate-win detection ────────────────────────────────────────

    def find_winning_move(self, board: List[List[int]],
                          player: int) -> Optional[Tuple[int, int]]:
        """Return a one-move win for *player*, or None."""
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

    # ── move-ordering heuristic ────────────────────────────────────────

    def _move_heuristic(self, board: List[List[int]],
                        r: int, c: int, player: int) -> int:
        """Heuristic score for placing *player* at (r,c)."""
        score = 0
        opp = WHITE if player == BLACK else BLACK

        # Offensive
        board[r][c] = player
        for dr, dc in DIRECTIONS:
            cnt, ends = self._count_through(board, r, c, dr, dc, player)
            if cnt >= 5:
                board[r][c] = EMPTY
                return 100_000_000
            score += PATTERN.get((cnt, ends), 0)
            score += self._gap_score(board, r, c, dr, dc, player)
        board[r][c] = EMPTY

        # Defensive
        board[r][c] = opp
        best_def = 0
        for dr, dc in DIRECTIONS:
            cnt, ends = self._count_through(board, r, c, dr, dc, opp)
            if cnt >= 5:
                board[r][c] = EMPTY
                return 99_999_999
            p = PATTERN.get((cnt, ends), 0)
            if p > best_def:
                best_def = p
            score += p * 12 // 10
            gp = self._gap_score(board, r, c, dr, dc, opp)
            score += gp * 12 // 10
            if gp > best_def:
                best_def = gp
        board[r][c] = EMPTY

        if best_def >= 200_000:       # also catch gap-threes (400K)
            score += best_def * 2      # double-boost defensive moves

        # Center bias (mild)
        center = self.size // 2
        score += max(0, 120 - (abs(r - center) + abs(c - center)) * 15)

        return score

    def order_moves(self, board: List[List[int]],
                    moves: List[Tuple[int, int]],
                    player: int,
                    depth: int = 0) -> List[Tuple[int, int]]:
        """Sort moves by heuristic score, with killer-move boost."""
        scored = []
        for r, c in moves:
            s = self._move_heuristic(board, r, c, player)

            # Killer boost
            if depth < len(self._killer):
                if (r, c) == self._killer[depth][0]:
                    s += 50_000
                elif (r, c) == self._killer[depth][1]:
                    s += 40_000

            scored.append((s, r, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [(r, c) for _, r, c in scored]

    # ── terminal detection ─────────────────────────────────────────────

    def _board_winner(self, board: List[List[int]]) -> Optional[int]:
        """Return the colour that already has 5-in-a-row, or None."""
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

    # ── quiescence search ──────────────────────────────────────────────

    def _quiesce(self, board: List[List[int]],
                 alpha: int, beta: int, player: int, ai_player: int,
                 start_t: float, deadline: float,
                 qdepth: int = 0) -> int:
        """Quiescence search: only consider forcing moves at leaf nodes.

        qdepth limits recursion (max 6 plies)."""
        if time.time() - start_t >= deadline:
            raise TimeoutError()
        if qdepth >= 6:
            return self.evaluate(board, ai_player)

        stand_pat = self.evaluate(board, player)

        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        opp = WHITE if player == BLACK else BLACK
        forcing_moves = set()

        # Own winning moves
        for r, c in self.candidates(board, 1):
            board[r][c] = player
            for dr, dc in DIRECTIONS:
                cnt, _ = self._count_through(board, r, c, dr, dc, player)
                if cnt >= 5:
                    forcing_moves.add((r, c))
                    break
            board[r][c] = EMPTY

        # Opponent's winning moves (must block)
        for r, c in self.candidates(board, 1):
            board[r][c] = opp
            for dr, dc in DIRECTIONS:
                cnt, _ = self._count_through(board, r, c, dr, dc, opp)
                if cnt >= 5:
                    forcing_moves.add((r, c))
                    break
            board[r][c] = EMPTY

        if not forcing_moves:
            return stand_pat

        for r, c in forcing_moves:
            board[r][c] = player
            try:
                v = -self._quiesce(board, -beta, -alpha, opp, ai_player,
                                   start_t, deadline, qdepth + 1)
            finally:
                board[r][c] = EMPTY
            if v >= beta:
                return beta
            if v > alpha:
                alpha = v

        return alpha

    # ── negamax search ─────────────────────────────────────────────────

    def _negamax(self, board: List[List[int]],
                 depth: int, alpha: int, beta: int,
                 player: int, ai_player: int,
                 start_t: float, deadline: float) -> int:
        """Negamax with alpha-beta pruning (same structure as AI 1)."""

        if time.time() - start_t >= deadline:
            raise TimeoutError()

        opp = WHITE if player == BLACK else BLACK

        # Terminal: board has winner (from *player*'s perspective)
        winner = self._board_winner(board)
        if winner == player:
            return 100_000_000 - (10 - depth)
        elif winner is not None:
            return -100_000_000 + (10 - depth)

        # Can current player win in one?
        if self.find_winning_move(board, player):
            return 100_000_000 - (10 - depth)

        if depth == 0:
            return self._quiesce(board, alpha, beta, player, ai_player,
                                 start_t, deadline)

        moves = self.candidates(board, 1)
        if not moves:
            return 0

        moves = self.order_moves(board, moves, player, depth=depth)
        moves = moves[:15]

        for r, c in moves:
            board[r][c] = player
            try:
                v = -self._negamax(board, depth - 1, -beta, -alpha,
                                   opp, ai_player, start_t, deadline)
            finally:
                board[r][c] = EMPTY

            if v >= beta:
                # Killer move
                if depth < len(self._killer):
                    if self._killer[depth][0] != (r, c):
                        self._killer[depth][1] = self._killer[depth][0]
                        self._killer[depth][0] = (r, c)
                return beta

            if v > alpha:
                alpha = v

        return alpha

    # ── public API ─────────────────────────────────────────────────────

    def get_best_move(self, board: List[List[int]],
                      player: int,
                      time_limit: float = 3.5) -> Tuple[int, int]:
        """Return the best move for *player*.

        Time management (same as AI 1):
          - opening (≤4 stones): 0.6 s
          - early game (5–12 stones): 1.5 s
          - mid game (13+ stones): time_limit (3.5 s)
        """

        stone_cnt = sum(1 for r in range(self.size) for c in range(self.size)
                        if board[r][c] != EMPTY)

        # First move — center
        if stone_cnt == 0:
            return (self.size // 2, self.size // 2)

        # Second move as white — search among nearby cells, not just adjacent
        if stone_cnt == 1 and player == WHITE:
            # Find opponent's stone
            for r in range(self.size):
                for c in range(self.size):
                    if board[r][c] == BLACK:
                        # Search radius 2 for a better opening
                        nearby = []
                        for dr in range(-2, 3):
                            for dc in range(-2, 3):
                                nr, nc = r + dr, c + dc
                                if 0 <= nr < self.size and 0 <= nc < self.size \
                                        and board[nr][nc] == EMPTY:
                                    nearby.append((nr, nc))
                        if nearby:
                            # Score and pick best
                            scored = [(self._move_heuristic(board, nr, nc, WHITE), nr, nc)
                                      for nr, nc in nearby]
                            scored.sort(key=lambda x: x[0], reverse=True)
                            return (scored[0][1], scored[0][2])

        # Adjust time limit — white gets more time (compensate first-move disadvantage)
        if stone_cnt <= 4:
            time_limit = 0.8
        elif stone_cnt <= 12:
            time_limit = 2.5 if player == WHITE else 1.5
        else:
            time_limit = 4.5 if player == WHITE else 3.5

        opp = WHITE if player == BLACK else BLACK

        # Immediate win
        win = self.find_winning_move(board, player)
        if win:
            return win

        # Must-block
        block = self.find_winning_move(board, opp)
        if block:
            return block

        # Candidate moves
        moves = self.candidates(board, 1)
        if len(moves) <= 1:
            return moves[0] if moves else (self.size // 2, self.size // 2)

        moves = self.order_moves(board, moves, player)
        best_move = moves[0]
        start = time.time()

        # Iterative deepening
        self._killer = [[None, None] for _ in range(18)]

        try:
            for depth in range(2, 16, 2):
                best_at_depth = None
                best_val = -10**18
                alpha = -10**18
                beta = 10**18

                search_moves = moves[:18]
                for r, c in search_moves:
                    if time.time() - start >= time_limit - 0.15:
                        raise TimeoutError()

                    board[r][c] = player
                    try:
                        v = -self._negamax(board, depth - 1, -beta, -alpha,
                                           opp, player, start, time_limit - 0.15)
                    finally:
                        board[r][c] = EMPTY

                    if v > best_val:
                        best_val = v
                        best_at_depth = (r, c)
                    if v > alpha:
                        alpha = v

                if best_at_depth is not None:
                    best_move = best_at_depth

                if best_val >= 99_999_990:
                    break

        except TimeoutError:
            pass

        return best_move
