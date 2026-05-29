# Advanced Gomoku Game (Gobang) with Multi-AI and PVP / 智能五子棋游戏（多模式对战）

<p align="center">
  <a href="#-english">English</a> •
  <a href="#-中文">中文</a>
</p>

---

## 🇺🇸 English

A feature-rich, Python-based Gomoku (Gobang) game supporting multiple gameplay modes and advanced game-tree search AIs.

### 🚀 Game Modes
* **PVP (Player vs Player):** Local two-player battle. Pass and play with your friend.
* **PVAI (Player vs AI):** Challenge the intelligent computer. You can choose to play against **AI 1** or **AI 2**.
* **AIVAI (AI vs AI):** Watch a simulation match where **AI 1** fights against **AI 2** to observe their tactical differences.

### 🛠️ File Structure
* `main.py` - Game entry point & menu interface.
* `gomoku_game.py` - Core game engine (rules, board state, win/loss judgment).
* `gomoku_ai.py` - Implementation of **AI 1** (Standard Minimax).
* `gomoku_ai2.py` - Implementation of **AI 2** (Advanced Negamax with enhanced pruning and sorting).

---

### 📊 Technical Comparison: AI 1 vs AI 2

| Feature | AI 1 (`gomoku_ai.py`) | AI 2 (`gomoku_ai2.py`) |
| :--- | :--- | :--- |
| **Search Algorithm** | Minimax + Alpha-Beta Pruning | Negamax + Alpha-Beta Pruning (Equivalent, more concise) |
| **Pattern Recognition** | **Consecutive stones only**: 9 patterns (e.g., `XXXX`, `XXX`) | **Consecutive + Broken patterns**: Added 4 jump patterns (e.g., `X_XXX`, `XX_XX`, `X_XX`) |
| **Leaf Nodes** | Returns static evaluation directly | **Quiescence Search** (`_quiesce`): Continues evaluating forced moves to avoid the Horizon Effect |
| **Move Ordering** | Pure heuristic scoring | Heuristic + **Killer Move** heuristic (Remembers pruning moves at each depth, searches them first) |
| **Transposition Table** | None | None (Initial Zobrist + TT was removed due to bugs) |
| **Opening Strategy** | White only clings to Black (Distance = 1) | Search radius = 2 (More flexible in controlling the center) |
| **Defense Weight** | 1.2× | 1.2× (Same), but defense heuristic threshold is lower (200K vs 500K), identifying threats earlier |
| **Thinking Time (White)**| Early game: ~1.5s / Mid game: ~3.5s | Early game: ~2.5s / Mid game: ~4.5s (Compensating for move order disadvantage) |
| **Search Width** | 12 moves | 15 moves (Root node: 18) |
| **Match Record** | — | **8 - 0 (Flawless victory over AI 1)** |

#### ⚠️ Shared Limitations (Both AIs)
Both models share the same underlying architecture (Negamax/Minimax + Alpha-Beta, Iterative Deepening depth 2-6, branching factor ~15), which leads to:
1. **Blind spots beyond 7 plies:** Unable to detect forced winning sequences longer than 7 moves.
2. **No "Double Threat" detection:** Lacks a dedicated check for creating two independent winning threats simultaneously (e.g., double-three or double-four) in a single move.
3. **Purely defensive nature:** They prioritize blocking the opponent and rarely initiate proactive strategic layouts.

---

### 🎮 How to Run
1. Ensure Python 3.8+ is installed.
2. Run the main entry:
   ```bash
   python main.py