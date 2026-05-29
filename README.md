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

---

## 🇨🇳 中文

一款功能丰富的基于 Python 开发的五子棋（Gobang）游戏，支持多种对战模式和基于博弈树搜索的高级 AI 算法。

### 🚀 游戏模式
* **PVP（玩家对战玩家）：** 本地双人对战，与好友轮流落子对弈。
* **PVAI（玩家对战AI）：** 挑战智能电脑对手，可选择与 **AI 1** 或 **AI 2** 对战。
* **AIVAI（AI对战AI）：** 观看 AI 模拟对战，观察 **AI 1** 与 **AI 2** 的战术差异。

### 🛠️ 文件结构
* `main.py` - 游戏入口文件 & 菜单界面。
* `gomoku_game.py` - 核心游戏引擎（规则判定、棋盘状态、胜负判断）。
* `gomoku_ai.py` - **AI 1** 实现（标准 Minimax 算法）。
* `gomoku_ai2.py` - **AI 2** 实现（进阶 Negamax 算法，含增强剪枝和落子排序）。

---

### 📊 技术对比：AI 1 vs AI 2

| 特性 | AI 1 (`gomoku_ai.py`) | AI 2 (`gomoku_ai2.py`) |
| :--- | :--- | :--- |
| **搜索算法** | 极小极大值（Minimax）+ α-β 剪枝 | 负极大值（Negamax）+ α-β 剪枝（效果等价，代码更简洁） |
| **棋型识别** | **仅连续棋型**：9 种（例如 `XXXX`、`XXX`） | **连续棋型 + 间断棋型**：新增 4 种跳棋型（例如 `X_XXX`、`XX_XX`、`X_XX`） |
| **叶节点处理** | 直接返回静态评估值 | **静态搜索（Quiescence Search）** (`_quiesce`)：对强制落子继续评估，避免“地平线效应” |
| **落子排序** | 纯启发式评分 | 启发式评分 + **杀手棋（Killer Move）** 启发（记录各深度的剪枝落子，优先搜索） |
| **置换表（Transposition Table）** | 无 | 无（初始的 Zobrist 哈希 + 置换表因 Bug 移除） |
| **开局策略** | 白棋仅紧贴黑棋落子（距离=1） | 搜索半径=2（控场更灵活，侧重中心区域） |
| **防守权重** | 1.2 倍 | 1.2 倍（与AI 1相同），但防守启发阈值更低（20万 vs 50万），更早识别威胁 |
| **思考耗时（白棋）** | 开局：~1.5秒 / 中局：~3.5秒 | 开局：~2.5秒 / 中局：~4.5秒（弥补落子排序的性能损耗） |
| **搜索宽度** | 12 步候选落子 | 15 步候选落子（根节点：18步） |
| **对战记录** | — | **8 - 0（对 AI 1 全胜）** |

#### ⚠️ 共同局限性（两款 AI）
两款 AI 共享相同的底层架构（Negamax/Minimax + α-β 剪枝、迭代加深深度 2-6、分支因子 ~15），导致以下问题：
1. **7步以上盲点：** 无法识别超过 7 步的强制获胜序列。
2. **无“双威胁”检测：** 缺乏专门逻辑检测“一步形成两个独立获胜威胁”（例如双三、双四）。
3. **纯防守性：** 优先封堵对手，极少主动构建进攻性战略布局。

---

### 🎮 运行方法
1. 确保安装 Python 3.8 及以上版本。
2. 运行主入口文件：
   ```bash
   python main.py