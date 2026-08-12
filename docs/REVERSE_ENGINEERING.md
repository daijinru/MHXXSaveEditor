# MHXX 存档逆向研究指南 (REVERSE_ENGINEERING.md)

> **这是 AI 进驻本项目的必读文档。**
> 目标：让任何 AI（不绑定具体模型）在 10 分钟内上手，按
> **假设 → 实验 → 证据 → 验证 → 固化** 的研究闭环，
> 对《怪物猎人 XX》(3DS) 存档格式做逆向分析。
>
> 配套文件：
> - `.workbuddy/skills/mhxx-reverse-research/SKILL.md` — AI 进驻的工作流入口
>   （WorkBuddy 技能格式，`agent_created`；任何 AI 打开本项目后应优先加载它）
> - `webapp/server.py` — 研究平台服务（零依赖）
> - `tools/` — CLI 工具（hexdump / patch / diff）
> - `data/offsets.json` — 43 个已知偏移（唯一权威源是 C# `Offsets.cs`）
> - `data/game_constants.json` — 67 张 ID→名称 映射表（21,098 条目）
> - `data/knowledge/` — 知识固化区（研究结论沉淀于此）
> - `experiments/` — 实验记录区（一次实验一个 md 文件）

---

## 0. 研究闭环方法论（最重要的章节）

存档逆向的本质是：**在 4,726,152 字节的二进制里，确定"哪段字节代表什么"**。
这个过程必须可复现、可审计、可沉淀。任何一次研究都按五步走：

```
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ 1.假设   │ → │ 2.实验   │ → │ 3.证据   │ → │ 4.验证   │ → │ 5.固化   │
│ 提出猜想 │   │ 设计改动 │   │ 采集数据 │   │ 复现确认 │   │ 沉淀知识 │
└─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

### 0.1 五步详解

| 步骤 | 做什么 | 用什么工具 | 产出物 |
|---|---|---|---|
| **1. 假设** | 基于已有知识提出"偏移 X 是字段 Y，类型 Z" | `GET /api/offsets`、`GET /api/constants/<表>` | 一句话假设，写入实验记录 |
| **2. 实验** | 设计**最小改动**：只改假设涉及的字节 | `POST /api/save/patch` 或 `tools/patch.py` | 补丁记录（old_hex → new_hex） |
| **3. 证据** | 采集两类证据：静态 diff / 游戏内观察 | `tools/diff.py`、`GET /api/save/diff`、游戏截图 | 证据链 |
| **4. 验证** | 边界验证（0、最大值、负值）、复现实验 | 重复 1-3 步 | 可复现的实验记录 |
| **5. 固化** | 把结论写入知识库，标注验证状态 | `POST /api/knowledge/<name>` | knowledge 条目 |

### 0.2 研究纪律（必须遵守）

1. **一次只验证一个假设**。补丁改动面越小，证据越干净。
2. **永不猜测**。没有证据的结论必须标注 `(待验证)`；证据不足就标记 `UNKNOWN`，不要"编一个合理值"。
3. **记录可复现**。每个实验记录必须包含：存档来源、补丁字节、操作步骤——另一个 AI 或人照着做能复现。
4. **修改前备份**。任何写回磁盘操作前，先复制一份原始存档。
5. **区分静态/动态证据**：
   - **静态证据**：AI 可以独立完成——对两个存档跑 diff，找出差异偏移。
   - **动态证据**：需要人类配合——在游戏里做动作（如"买一件装备"）→ 导出存档 → diff。AI 负责分析，人类负责操作。
6. **怀疑已知**。`data/offsets.json` 来自原 C# 编辑器，部分注释带 `(supposedly)`（如 MONSTERHUNT_OFFSETS 写 "137 Monsters (supposedly)"）——这些是**未经验证的假设**，正是研究的起点。

### 0.3 证据分级

| 等级 | 含义 | 可写进知识库吗 |
|---|---|---|
| ⚪ UNKNOWN | 无证据 | 只能作为"待研究问题" |
| 🟡 HYPOTHESIS | 有推断无验证 | 标注 `(待验证)` |
| 🟢 CONFIRMED | 静态验证（diff 逻辑自洽） | 可固化，标注证据类型 |
| 🔵 VERIFIED | 游戏内动态验证 | 可固化，优先级别最高 |

---

## 1. 快速上手

### 1.1 启动服务

```bash
python webapp/server.py --port 8765
# 数据目录默认 data/，可用 --data-dir 覆盖
```

### 1.2 加载存档

3DS 的存档文件（通常是 `system`，4,726,152 字节）需先从 3DS 导出：

```bash
# 方式一：服务内加载
curl -X POST http://127.0.0.1:8765/api/save/load \
  -H "Content-Type: application/json" \
  -d '{"path": "C:/path/to/system"}'

# 方式二：浏览器上传（Web 界面右上角）
```

### 1.3 最小研究流程示例（验证金钱偏移）

> 目标：验证 `FUNDS_OFFSET = 0x24` 是否真的是金钱（uint32 LE）。

```bash
# ① 假设：0x24 处是 uint32 LE 金钱
# ② 读取当前值
curl "http://127.0.0.1:8765/api/save/bytes?offset=0x24&length=4"
# → {"bytes": [E7, 03, 00, 00]}  → 0x000003E7 = 999

# ③ 实验：改成 123456
curl -X POST http://127.0.0.1:8765/api/save/patch \
  -H "Content-Type: application/json" \
  -d '{"offset": 36, "hex": "40 E2 01 00"}'
# 0x0001E240 = 123456 ✓

# ④ 写回 → 复制到 3DS → 进游戏看金钱是否 123456
curl -X POST http://127.0.0.1:8765/api/save/write -d '{}'

# ⑤ 游戏内确认 → 固化
curl -X POST http://127.0.0.1:8765/api/knowledge/known-offsets \
  -H "Content-Type: application/json" \
  -d '{"append": "| FUNDS_OFFSET | 0x24 | uint32 LE 金钱 (VERIFIED 2026-08-12 游戏内确认) |"}'
```

---

## 2. 已知格式知识库

### 2.1 存档总览

| 属性 | 值 |
|---|---|
| 文件大小 | **4,726,152 字节**（固定，服务器强校验） |
| 字节序 | **Little-Endian** |
| 角色槽位 | 3 个，`raw[4]` / `raw[5]` / `raw[6]` == 1 表示启用 |
| 角色偏移 | 每槽一个 uint32 LE 指针（0x10 / 0x14 / 0x18），指向该角色数据基址 |

### 2.2 头部区域（相对文件开头）

| 偏移 | 名称 | 类型 | 说明 |
|---|---|---|---|
| 0x04 | FIRST_CHAR_SLOT_USED | u8 | 槽位 1 是否启用 |
| 0x05 | SECOND_CHAR_SLOT_USED | u8 | 槽位 2 |
| 0x06 | THIRD_CHAR_SLOT_USED | u8 | 槽位 3 |
| 0x10 | FIRST_CHARACTER_OFFSET | u32 | 角色 1 数据指针 |
| 0x14 | SECOND_CHARACTER_OFFSET | u32 | 角色 2 数据指针 |
| 0x18 | THIRD_CHARACTER_OFFSET | u32 | 角色 3 数据指针 |
| 0x20 | PLAY_TIME_OFFSET | u32 | 游戏时间（只在存档界面显示） |
| 0x24 | FUNDS_OFFSET | u32 | 金钱（只在存档界面显示） |
| 0x28 | HUNTER_RANK_OFFSET | u16 | 猎人等级 |

### 2.3 角色数据（相对角色基址）

> 偏移常量来自 `Offsets.cs`，注释为 "Character Offsets [CHARACTER BASE + CHARACTER OFFSET]"，
> 即**实际地址 = 角色基址 + 下列偏移**（不是文件绝对偏移）。

| 字段 | 偏移常量 | 数值 | 类型 |
|---|---|---|---|
| NAME | NAME_OFFSET | 0x23B7D | 字符串 |
| 语音 / 瞳色 / 服装 / 性别 | VOICE / EYE_COLOR / CLOTHING / GENDER | 0x23B48 起 4 个连续 u8 | u8 |
| 狩猎风格 / 发型 / 脸型 / 特征 | HUNTINGSTYLE / HAIRSTYLE / FACE / FEATURES | 0x23B4C 起 4 个连续 u8 | u8 |
| 肤色 RGBA | SKIN_COLOR | 0x23B67 | u8×4 |
| 特征色 RGBA | FEATURES_COLOR | 0x23B6F | u8×4 |

> 观察：上述 u8 字段在 0x23B48–0x23B4F 连续排列（间隔 1 字节），
> 颜色字段为 4 字节。此布局为原编辑器字段顺序的推断，精确结构待研究（见 Backlog #9）。
> 各据点数为独立绝对偏移：HR_POINTS 0x280B、ACADEMY 0x2817、BHERNA 0x281B、KOKOTO 0x281F、POKKE 0x2823、YUKUMO 0x2827（均 u32）。

### 2.4 大区块结构（已由原编辑器确认）

| 区块 | 偏移 | 结构 | 说明 |
|---|---|---|---|
| ITEM_BOX | 0x278 | 2300 格 × 19 bits | 道具箱（物品 ID + 数量压缩在 19 bits） |
| MONSTERHUNT | 0x5EA6 | 137 只 × 2 字节 | 讨伐数（supposedly） |
| MONSTERCAPTURE | 0x5FB8 | 137 只 × 2 字节 | 捕获数（supposedly） |
| MONSTERSIZE | 0x60CA | 137 只 × 4 字节 | 体型 |
| EQUIPMENT_BOX | 0x62EE | 2000 件 × 36 字节 | 装备箱 |
| PALICO_EQUIPMENT | 0x17C2E | 1000 件 × 36 字节 | 随从猫装备 |
| PALICO | 0x23BB6 | 84 只 × 324 字节 | 随从猫数据 |
| GUILDCARD | 0xC71BD | — | 公会卡片 |
| MANUAL_SHOUTOUT | 0x11D629 | 60 字节 | 手动快捷短语 |
| AUTOMATIC_SHOUTOUT | 0x11E169 | 60 字节 | 自动快捷短语 |

> **注意**：ITEM_BOX 每格 19 bits 意味着道具箱不是"每格固定字节"，解析时需按位域切分——这是原编辑器 `DataExtractor` 的核心逻辑，也是研究/改写的难点之一。

### 2.5 ID 映射表（data/game_constants.json）

67 张表，21,098 条目。常用表：

| 表名 | 内容 |
|---|---|
| `ItemNameList` | 物品 ID → 名称（**道具研究的核心表**） |
| `EquipGreatSwordNames` ~ `EquipGunlanceNames` | 14 种武器 ID → 名称 |
| `EquipHead/Chest/Arms/Waist/LegsNames` (+IDs) | 防具 ID → 名称 |
| `JwlNames` + `JwlIDs` | 装饰珠 |
| `SkillNames` | 技能 |
| `EquipTalismanNames` | 护石 |
| `KinsectNames` | 猎虫 |
| `PalicoSkills` / `PalicoSkills1-3` | 随从猫技能 |
| `MonsterHuntNames` | 怪物 ID → 名称（**配合讨伐数偏移**） |
| `PoogieCostumes` / `FeniCostumes` | 小猪/菲尼服装 |

**使用方式**：
```bash
# 列出所有表
curl http://127.0.0.1:8765/api/constants
# 取单张表
curl http://127.0.0.1:8765/api/constants/ItemNameList
```

---

## 3. 工具指南

### 3.1 Web API 完整参考

服务地址 `http://127.0.0.1:8765`，全部返回 JSON。

**存档操作**

| 方法 | 路径 | 参数 | 说明 |
|---|---|---|---|
| GET | `/api/save/status` | — | 当前加载状态 / 路径 / 大小 |
| POST | `/api/save/load` | `{"path": "绝对路径"}` | 从磁盘加载（强校验 4,726,152 字节） |
| POST | `/api/save/upload` | `{"name": "...", "data_b64": "base64"}` | 上传存档 |
| GET | `/api/save/bytes` | `offset`、`length` | 读原始字节 → `{"bytes": [...]}` |
| GET | `/api/save/hex` | `offset`、`length` | 读 hex 行（16 字节/行，含 ASCII） |
| POST | `/api/save/patch` | `{"offset": 36, "hex": "FF E0 F5 05"}` 或 `{"offset": 36, "bytes": [1,2]}` | 内存打补丁，返回 old/new hex |
| POST | `/api/save/write` | `{"path": "可选"}` | 写回磁盘（默认覆盖原路径） |
| GET | `/api/save/download` | — | 下载当前内存存档 |
| GET | `/api/save/diff` | `offset`、`length` | 磁盘快照 vs 内存差异 → `{"changes": [{offset, old, new}]}` |

**数据查询**

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/offsets` | 全部 43 个偏移（name/offset/comment） |
| GET | `/api/constants` | 表名 + 条目数 |
| GET | `/api/constants/<表名>` | 单张 ID→名称 映射表 |

**研究记录**

| 方法 | 路径 | 参数 | 说明 |
|---|---|---|---|
| GET | `/api/experiments` | — | 实验列表 |
| GET | `/api/experiments/<文件名>` | — | 单条实验内容 |
| POST | `/api/experiment` | `{"title","hypothesis","method","evidence","conclusion"}` | 创建实验记录 → `experiments/时间戳_标题.md` |
| GET | `/api/knowledge/<名>` | — | 读取知识库 md |
| POST | `/api/knowledge/<名>` | `{"append": "markdown 行"}` | 追加知识（带时间戳） |

**参数约定**：`offset`/`length` 接受十进制或 `0x` 前缀十六进制；`patch` 支持 `hex` 字符串（忽略空格）或 `bytes` 数组。

### 3.2 CLI 工具

```bash
# hexdump：按偏移查看（AI 的最常用工具）
python tools/hexdump.py save/system --offset 0x24 --length 16 --ascii

# patch：应用补丁（默认覆盖原文件，务必先备份！）
python tools/patch.py apply save/system 0x24 "00 00 00 00" --out save/patched.bin

# patch export：对比两存档导出 JSON 补丁清单（可提交进仓库复现实验）
python tools/patch.py export save/base.bin save/modified.bin --out patch.json

# diff：对比两存档，找差异（验证"游戏内动作 → 哪个字节变了"）
python tools/diff.py save/before.bin save/after.bin --limit 100
```

### 3.3 数据文件结构

**`data/offsets.json`**（数组）：
```json
[{"name": "FUNDS_OFFSET", "offset": 36, "comment": "Size 4, this only shows on the save screen"}]
```

**`data/game_constants.json`**（对象，键为表名）：
```json
{"ItemNameList": ["", "やまびこそう", "..."]}
```

> 两个 JSON 均由 `tools/extract.py` 从 C# 源码生成。**C# 源码是唯一权威源**：
> 修改 `Offsets.cs` / `GameConstants.cs` 后重跑 `python tools/extract.py` 即可重新生成。

---

## 4. 实验记录规范

### 4.1 文件模板

每次实验在 `experiments/` 下生成一个 md 文件（API 自动生成骨架）：

```markdown
# <实验标题>

- 创建时间: YYYY-MM-DD HH:MM:SS
- 存档: <存档路径或来源>

## 假设 (Hypothesis)
<一句话：偏移 X 是字段 Y，类型 Z>

## 实验方法 (Method)
<最小改动：改了哪些字节，怎么改的>

## 证据 (Evidence)
<静态证据：diff 输出 / hexdump；动态证据：游戏内观察结果>

## 结论 (Conclusion)
<结论 + 证据等级：⚪UNKNOWN / 🟡HYPOTHESIS / 🟢CONFIRMED / 🔵VERIFIED>
```

### 4.2 命名规范

- 文件名由 API 自动生成：`YYYYMMDD_HHMMSS_标题前40字符.md`
- 标题要能描述假设，如 `验证FUNDS_OFFSET_0x24为金钱_uint32LE`

### 4.3 知识固化格式

向 `data/knowledge/known-offsets.md` 追加（API 自动带时间戳）：
```markdown
| <偏移名> | 0x<偏移> | <类型与说明> (VERIFIED YYYY-MM-DD 验证方式) |
```

新主题知识（如"道具箱 19bits 位域解析"）可建新文件：
```bash
curl -X POST http://127.0.0.1:8765/api/knowledge/item-box-format \
  -H "Content-Type: application/json" \
  -d '{"append": "道具箱每格 19 bits: ..."}'
```

---

## 5. 待研究问题清单（Backlog）

以下问题来自原 C# 代码注释中的不确定性，**是现成的研究起点**：

| # | 问题 | 线索 | 状态 |
|---|---|---|---|
| 1 | MONSTERHUNT_OFFSETS 是否真的是 137 只 × 2 字节？ | 注释标 `(supposedly)`；对照 `MonsterHuntNames` 表（核对怪物数） | ⚪ UNKNOWN |
| 2 | MONSTERCAPTURE_OFFSETS 结构是否与讨伐数一致？ | 同上 | ⚪ UNKNOWN |
| 3 | ITEM_BOX 每格 19 bits 的确切位域布局（ID 占几位、数量占几位）？ | 原 `DataExtractor.cs` 解析逻辑（对照源码） | 🟡 HYPOTHESIS |
| 4 | 装备箱每件 36 字节的字段布局（武器类型/强化/孔位/幻化）？ | 原编辑器 `Transmogrify.cs`、`EditTalismanDialog.cs` | 🟡 HYPOTHESIS |
| 5 | 金钱修改是否需要校验和？直接改 0x24 后游戏是否报错？ | FUNDS_OFFSET 注释 "only shows on the save screen" | ⚪ UNKNOWN |
| 6 | PLAY_TIME_OFFSET (0x20) 与 PLAY_TIME_OFFSET2 (0x2248B) 的关系？ | 两处都有游戏时间 | ⚪ UNKNOWN |
| 7 | 各据点数偏移是否还有其他据点数遗漏？ | Player.cs 有 6 个 Points 字段 | ⚪ UNKNOWN |
| 8 | 快捷短语 60 字节是定长 UTF-16 还是 6 条 × 10 字节？ | 原 `EditShoutoutsDialog.cs` | 🟡 HYPOTHESIS |
| 9 | 角色数据区 0x23B48 起各字段的精确布局（含名字与颜色区间的未知字节）？ | 相邻 u8 字段连续；NAME_OFFSET 距 VOICE 53 字节 | 🟡 HYPOTHESIS |

> 研究完一个，把结论固化到知识库，并在此表更新状态。研究过程中发现的新问题，追加到表尾。
