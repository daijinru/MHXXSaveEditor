---
name: mhxx-reverse-research
description: 让任意 AI 进驻 MHXXSaveEditor 项目，对《怪物猎人XX》(3DS) 存档（4,726,152 字节二进制）做逆向研究的入口工作流。当 AI 需要在本项目内定位存档字段、验证偏移假设、解析道具/装备/护石/随从猫数据结构、探索校验和、或建立 ID 映射关系时使用。技能定义完整进驻流程：启动零依赖 Web 研究平台 → 读取必读文档 docs/REVERSE_ENGINEERING.md → 加载存档 → 用 REST API 与 CLI 工具开展「假设-实验-证据-验证-固化」研究闭环 → 记录到 experiments/ → 固化到 data/knowledge/。运行时零第三方依赖，不绑定任何特定 LLM。
agent_created: true
---

# MHXX 存档逆向研究 —— AI 进驻工作流

## 用途

本项目是一个**存档逆向研究平台**（由原 C# WinForms 编辑器改造而来）：AI 在项目内对
《怪物猎人XX》3DS 存档做可复现、可审计、可沉淀的格式逆向。本技能定义 AI 进驻的完整
工作流。**详细方法论、格式知识、API 参考都在 `docs/REVERSE_ENGINEERING.md`，本文件
只给工作流骨架，两者必须配合使用。**

## 进驻流程（按序执行）

### Step 0 前置确认

- 工作目录必须是项目根 `MHXXSaveEditor/`（所有相对路径以此为准）。
- 确认 Python 3.8+ 可用（本项目无任何第三方依赖，标准库即可）。

### Step 1 读取必读文档

完整读取 `docs/REVERSE_ENGINEERING.md`，至少覆盖：

- **§0 研究闭环方法论** —— 五步闭环与 6 条研究纪律（不可跳过）
- **§2 已知格式知识库** —— 偏移表、大区块结构、ID 映射表
- **§3 工具指南** —— API 与 CLI 的完整参数
- **§5 Backlog** —— 9 个现成研究起点

### Step 2 启动服务并加载存档

```bash
# 启动研究平台（默认端口 8765，数据目录 data/）
python webapp/server.py --port 8765 &

# 健康检查
curl -s http://127.0.0.1:8765/api/health

# 加载存档（路径用绝对路径；存档通常是从 3DS 导出的 system 文件）
curl -X POST http://127.0.0.1:8765/api/save/load \
  -H "Content-Type: application/json" \
  -d '{"path": "C:/path/to/system"}'
```

无真实存档时，可先加载测试存档 `tests/save_test.bin` 熟悉工具链。

### Step 3 选择研究起点

优先从 `docs/REVERSE_ENGINEERING.md` §5 Backlog 选题（原 C# 注释里的 `(supposedly)`
疑点是最佳起点），或用户指定目标。一次只研究一个问题。

### Step 4 执行研究闭环（核心循环）

每个假设严格走五步，产出物逐级递进：

| 步骤 | 操作 | 工具 |
|---|---|---|
| **1. 假设** | 写下一句话假设："偏移 X 是字段 Y，类型 Z" | `GET /api/offsets`、`GET /api/constants/<表名>` |
| **2. 实验** | 设计最小改动，只改假设涉及的字节 | `POST /api/save/patch` 或 `tools/patch.py` |
| **3. 证据** | 采集静态 diff / 游戏内观察两类证据 | `tools/diff.py`、`GET /api/save/diff` |
| **4. 验证** | 边界值（0 / 最大值）与复现实验 | 重复 1-3 |
| **5. 固化** | 结论写入知识库，标注证据等级 | `POST /api/knowledge/<名>` |

```bash
# 示例：验证 FUNDS_OFFSET=0x24 是金钱（uint32 LE）
# 读当前值
curl "http://127.0.0.1:8765/api/save/bytes?offset=0x24&length=4"
# 改 123456（注意：offset 参数可写 0x24，但 JSON body 里不能写 0x 字面量！）
curl -X POST http://127.0.0.1:8765/api/save/patch \
  -H "Content-Type: application/json" \
  -d '{"offset": 36, "hex": "40 E2 01 00"}'
# 写回磁盘 → 用户复制到 3DS → 游戏内观察 → 用户反馈
curl -X POST http://127.0.0.1:8765/api/save/write -d '{}'
```

### Step 5 记录实验

每次实验生成一个 md 文件到 `experiments/`（API 自动命名）：

```bash
curl -X POST http://127.0.0.1:8765/api/experiment \
  -H "Content-Type: application/json" \
  -d '{"title": "验证FUNDS_OFFSET_0x24为金钱_uint32LE", "hypothesis": "...", "method": "...", "evidence": "...", "conclusion": "..."}'
```

记录必须可复现：含存档来源、补丁字节（old → new）、操作步骤。

### Step 6 固化知识

结论经验证后追加到 `data/knowledge/`（API 自动带时间戳）：

```bash
curl -X POST http://127.0.0.1:8765/api/knowledge/known-offsets \
  -H "Content-Type: application/json" \
  -d '{"append": "| FUNDS_OFFSET | 0x24 | uint32 LE 金钱 (VERIFIED 2026-08-12 游戏内确认) |"}'
```

研究完一个 Backlog 问题后，同步更新 `docs/REVERSE_ENGINEERING.md` §5 的状态列。
研究过程中发现的新疑点，追加到表尾（保持 ⚪ UNKNOWN）。

## 研究纪律（浓缩版，详见文档 §0.2）

1. **一次只验证一个假设**——补丁改动面越小，证据越干净。
2. **永不猜测**——无证据的结论标 `(待验证)`，证据不足标 `UNKNOWN`。
3. **记录可复现**——另一个 AI 或人照记录能复现实验。
4. **修改前备份**——任何写回磁盘前先复制原始存档。
5. **区分静态/动态证据**——静态（diff）AI 独立完成；动态（游戏内观察）必须请求
   人类配合：AI 设计改动并分析，人类进游戏操作并反馈。
6. **怀疑已知**——`data/offsets.json` 来自原 C# 编辑器，带 `(supposedly)` 注释的
   条目是未验证假设，正是研究起点。

## 命令速查

### REST API（服务地址 http://127.0.0.1:8765，全部返回 JSON）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/save/status` | 加载状态 |
| POST | `/api/save/load` | 从磁盘加载 `{"path": "..."}` |
| POST | `/api/save/upload` | 上传 `{"name", "data_b64"}` |
| GET | `/api/save/bytes?offset=&length=` | 读原始字节 |
| GET | `/api/save/hex?offset=&length=` | 读 hex 行（含 ASCII） |
| POST | `/api/save/patch` | 打补丁 `{"offset": 36, "hex": "FF E0 F5 05"}` 或 `"bytes": [..]` |
| POST | `/api/save/write` | 写回磁盘 |
| GET | `/api/save/download` | 下载内存存档 |
| GET | `/api/save/diff?offset=&length=` | 磁盘快照 vs 内存差异 |
| GET | `/api/offsets` | 43 个已知偏移（name/offset/comment） |
| GET | `/api/constants` | 表名 + 条目数 |
| GET | `/api/constants/<表名>` | 单张 ID→名称 映射表 |
| POST | `/api/experiment` | 创建实验记录 |
| GET | `/api/experiments` | 实验列表 |
| GET | `/api/experiments/<文件名>` | 单条实验 |
| GET | `/api/knowledge/<名>` | 读知识库 md |
| POST | `/api/knowledge/<名>` | 追加知识 `{"append": "markdown"}` |

### CLI 工具（研究时优先用 API，批量/对比用 CLI）

```bash
python tools/hexdump.py save/system --offset 0x24 --length 16 --ascii   # 按偏移看字节
python tools/patch.py apply save/system 0x24 "00 00 00 00" --out save/patched.bin  # 打补丁（先备份！）
python tools/patch.py export save/a.bin save/b.bin --out patch.json     # 导出补丁清单（可提交复现）
python tools/diff.py save/before.bin save/after.bin --limit 100         # 两存档找差异
```

### 数据文件（只读，勿手改）

- `data/offsets.json` —— 43 个偏移（权威源是 `MHXXSaveEditor/Data/Offsets.cs`）
- `data/game_constants.json` —— 67 张 ID 映射表（权威源 `GameConstants.cs`）
- 修改 C# 源码后运行 `python tools/extract.py` 重新生成 JSON

## 常见陷阱

- **JSON 里不能写 `0x` 字面量**：patch 请求的 `offset` 字段用十进制（`0x24` → `36`）；
  查询参数（`?offset=0x24`）才支持十六进制。
- **patch 的 bytes 数组是按字节序的原始字节**：uint32 LE 金钱 99999999 =
  `FF E0 F5 05`（低字节在前）。
- **写回磁盘不可逆**：写回前先 `cp` 一份原始存档；或先 `patch apply --out` 到新文件。
- **动态验证离不开人类**：AI 无法进游戏，游戏内观察结果必须由人类提供并记录到实验。

## 交付约定

- 研究结论的最终归宿是 `data/knowledge/`，实验过程留在 `experiments/`。
- 每次有效研究（有结论或新发现）后，向用户汇报：假设、证据等级、结论、下一步。
- 若用户要求提交代码，把新知识/新实验一起 `git add`（`data/knowledge/`、
  `experiments/`、更新后的 `docs/REVERSE_ENGINEERING.md` §5）。
