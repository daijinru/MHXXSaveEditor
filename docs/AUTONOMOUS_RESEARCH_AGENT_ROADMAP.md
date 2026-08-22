---
project: autonomous-binary-research-agent
created: 2026-08-22 13:53
last_updated: 2026-08-22 13:53
status: active
current_milestone: 1
total_milestones: 6
completed_milestones: 0
---

# 🗺️ 有边界的自主二进制研究智能体 — 实施路线图

## 需求概述

将 MHXX AI Research Studio 从“供外部 Agent 调用的存档工具”升级为一个有边界的自主研究智能体。用户给出研究目标或一组修改前／后的存档后，系统能够自主收集上下文、分析差异、提出候选字段假设、选择信息增益较高的下一项实验，并在高风险动作和游戏内动态验证前请求人工批准。

第一版只覆盖“验证一个已知或候选偏移是否对应某个字段”这一条闭环。MHXX 是首个领域 Adapter 和可重复验证环境；不在第一版扩展到任意可执行文件逆向或通用知识工作。

系统以证据而非模型输出作为结论依据。每项结论必须能够追溯到存档指纹、差异、补丁、验证结果和实验报告；服务重启后可以恢复未完成研究，并避免重复执行非幂等动作。

## 成功指标

- **Time to Verified Field**：从创建目标到得到动态验证结论的时间。
- **Human Actions per Verified Claim**：每个已验证结论需要的人工操作数。
- **False Consolidation Rate**：错误结论进入知识库的比例，目标为 0。
- **Resume Success Rate**：重启后无重复副作用地恢复研究的成功率，目标为 100%。
- **Reproduction Rate**：另一用户根据报告复现实验的成功率。

## 技术边界

- **涉及模块**：`webapp/server.py`、新增 Research Domain/Store/Controller、`webapp/static/`、`experiments/`、`data/knowledge/`、`tests/`。
- **技术栈约束**：Python 标准库、`ThreadingHTTPServer`、原生 HTML/CSS/JavaScript；保持零第三方运行时依赖。
- **安全边界**：只读分析可自动执行；修改内存副本和导出测试存档需要批准；覆盖原存档、动态验证和知识固化必须由用户显式确认。
- **兼容性**：保留现有 `/api/save/*`、`/api/experiment` 和 `/api/knowledge/*` 行为，新增接口采用 `/api/researches` 命名空间。
- **不做什么**：不实现反编译器；不重做通用 Hex 编辑器；不允许 Agent 自行声称完成人工动态验证；不在第一版接入多个模型供应商；不支持多用户远程部署。

---

## 目标架构

```text
用户目标 / before-after 样本
            │
            ▼
Research Controller ─────── Policy / Human Gate
  观察 → 决策 → 执行 → 评估       │
            │                     │批准/验证
            ▼                     ▼
      Research Domain ←──── Research Trace Store
            │                     │
            ▼                     ▼
   MHXX Tool Adapters       报告 / 知识 / Artifacts
```

核心职责：

- **Research Domain**：目标、假设、证据、阶段、结论和状态迁移。
- **Research Controller**：根据当前状态选择且只选择一个下一动作。
- **Policy**：判断动作可自动执行、需要批准还是必须人工完成。
- **Research Trace Store**：原子持久化、幂等、恢复和审计。
- **MHXX Tool Adapters**：槽位解析、字节读取、补丁、diff 和存档导出。

---

## 里程碑总览

| 序号 | 里程碑 | 状态 | 步骤数 | 完成数 |
|------|--------|------|--------|--------|
| M1 | 领域契约与测试基线 | 🔵 进行中 | 4 | 0 |
| M2 | 可恢复的研究轨迹 | ⬚ 待开始 | 4 | 0 |
| M3 | before/after 差异推断 | ⬚ 待开始 | 4 | 0 |
| M4 | 有边界的自主 Controller | ⬚ 待开始 | 4 | 0 |
| M5 | 人机审批与验证界面 | ⬚ 待开始 | 3 | 0 |
| M6 | 报告、知识固化与基准评估 | ⬚ 待开始 | 4 | 0 |

---

## M1: 领域契约与测试基线

**目标**: 在实现业务逻辑前固定研究状态、证据身份、权限规则和可执行测试入口。
**状态**: 🔵 进行中

### 步骤

- [ ] **S1.1**: 修订 Research Trace 设计为自主研究 Agent 设计
  - 验收: `rg -n "Research Controller|phase|verdict|Human Gate|save_fingerprint" docs/RESEARCH_TRACE_DESIGN.md` 能找到全部核心概念，文档不再将 `recorded`/`consolidated` 定义为研究状态。
  - 产出: 更新 `docs/RESEARCH_TRACE_DESIGN.md`，补充目标架构、信任模型和 MVP 用例。

- [ ] **S1.2**: 定义 Research、Hypothesis、Evidence、Artifact 和 TraceEvent 的版本化 JSON schema
  - 验收: 使用 `python -m unittest tests.test_research_schema` 验证合法样本通过，非法阶段、缺失指纹、未知 schema 版本被拒绝。
  - 产出: `webapp/research/schema.py`、`tests/test_research_schema.py`、示例 JSON fixtures。

- [ ] **S1.3**: 定义状态迁移和动作权限矩阵
  - 验收: `python -m unittest tests.test_research_policy` 通过，并覆盖自动、审批后执行、必须人工完成及非法 `VERIFIED` 四类路径。
  - 产出: `webapp/research/policy.py`、`tests/test_research_policy.py`。

- [ ] **S1.4**: 建立标准库 unittest 测试入口和隔离临时数据目录
  - 验收: `python -m unittest discover -s tests -p 'test_*.py'` 返回 0，测试不会修改仓库内 `experiments/`、`data/knowledge/` 或 `tests/save_test.bin`。
  - 产出: `tests/__init__.py`、测试 helpers、最小冒烟测试。

---

## M2: 可恢复的研究轨迹

**目标**: 研究能够被创建、审计、并发安全地更新，并在服务重启后恢复。
**状态**: ⬚ 待开始

### 步骤

- [ ] **S2.1**: 实现 Research Domain 的命令式 interface 和状态迁移
  - 验收: `python -m unittest tests.test_research_domain` 通过，调用者不能直接伪造系统事件或绕过结论前置条件。
  - 产出: `webapp/research/domain.py`、领域命令与结果类型。

- [ ] **S2.2**: 实现原子 JSON Store、版本冲突和幂等请求
  - 验收: `python -m unittest tests.test_research_store` 通过，覆盖临时文件替换、重复 `request_id`、陈旧 `version`、损坏文件和并发写入。
  - 产出: `webapp/research/store.py`、`experiments/traces/` 存储约定。

- [ ] **S2.3**: 实现存档和 artifact 指纹
  - 验收: 对同一输入重复计算得到相同 SHA-256；改变一个字节后指纹不同；研究绑定存档与当前存档不一致时测试返回明确错误。
  - 产出: `webapp/research/artifacts.py`、存档 fingerprint 与 artifact metadata。

- [ ] **S2.4**: 提供研究创建、列表、详情和领域命令 API
  - 验收: 启动临时服务器后，可通过 HTTP 创建研究、读取时间线、提交假设；非法迁移返回 409，非法输入返回 400，现有 API 冒烟测试仍通过。
  - 产出: `/api/researches` 路由、API 集成测试和错误响应约定。

---

## M3: before/after 差异推断

**目标**: 从成对存档中生成可解释、可排序的字段候选，而不依赖模型自由猜测。
**状态**: ⬚ 待开始

### 步骤

- [ ] **S3.1**: 实现不可变 before/after snapshot 和结构化 diff artifact
  - 验收: `python -m unittest tests.test_snapshot_diff` 通过；保存操作不会改变已记录 diff 的基线；diff 可在服务重启后读取。
  - 产出: `webapp/research/diffing.py`、snapshot/diff artifact JSON。

- [ ] **S3.2**: 实现差异连续区间聚类、槽相对地址换算和已知偏移关联
  - 验收: 对 `tests/save_test.bin` 的合成修改能输出绝对偏移、槽号、槽相对偏移和匹配的已知字段名。
  - 产出: 差异 region analyzer、MHXX 地址 Adapter、单元测试。

- [ ] **S3.3**: 实现常见字段编码解释和候选排名
  - 验收: fixtures 中的 `u8/u16/u32/i32/float/string/bit-field duplicate` 候选排序符合预期，并为每项候选返回评分明细而非单一模型结论。
  - 产出: `webapp/research/candidates.py`、确定性评分规则和测试语料。

- [ ] **S3.4**: 提供样本导入、动作描述、diff 分析和候选查询 API
  - 验收: 使用 HTTP 上传 before/after、提交“金钱增加”等观察后，响应包含候选列表、证据引用和下一步所需信息。
  - 产出: snapshot/diff/candidate API、端到端集成测试。

---

## M4: 有边界的自主 Controller

**目标**: 系统能够根据研究目标和证据自主选择下一项安全动作，并在边界处暂停。
**状态**: ⬚ 待开始

### 步骤

- [ ] **S4.1**: 实现确定性的 `observe → choose_next_action → execute → evaluate` 循环
  - 验收: `python -m unittest tests.test_research_controller` 通过；每次 `run_next` 至多产生一个外部动作，并能到达等待批准、等待验证或完成状态。
  - 产出: `webapp/research/controller.py`、NextAction 类型和控制循环测试。

- [ ] **S4.2**: 实现最小实验设计策略
  - 验收: 对多个候选选择能最大化候选区分度且修改字节最少的测试值；越界、原值相同和多字段修改方案被拒绝。
  - 产出: `webapp/research/experiment_planner.py`、实验计划与解释。

- [ ] **S4.3**: 接入补丁、diff、导出 Adapter 和审批令牌
  - 验收: 只读动作可自动执行；内存补丁必须持有匹配研究、版本、动作摘要的未过期批准；重复提交不会重复修改或记录事件。
  - 产出: Tool Adapter interface、MHXX adapters、approval command/API。

- [ ] **S4.4**: 实现暂停、恢复、失败预算和停止条件
  - 验收: Controller 在服务重启后从最后一个已提交事件继续；连续无信息增益、工具失败达到阈值或缺少人工输入时停止并给出结构化原因。
  - 产出: resume/retry 规则、失败分类、恢复集成测试。

---

## M5: 人机审批与验证界面

**目标**: 用户能够理解 Agent 正在做什么、批准风险动作，并用最少输入完成游戏内验证。
**状态**: ⬚ 待开始

### 步骤

- [ ] **S5.1**: 在右栏实现当前研究摘要，并以抽屉或弹窗承载完整时间线
  - 验收: 浏览器中可选择研究、查看目标/阶段/结论/下一动作；右栏数值解析、实验记录和知识库仍可正常使用；窄窗口下无关键按钮不可达。
  - 产出: 更新 `webapp/static/index.html`、`app.js`、`style.css`。

- [ ] **S5.2**: 实现结构化审批和人工验证任务卡片
  - 验收: 卡片明确显示目标文件、修改范围、预期观察、回滚方式和结果输入；未经用户操作不能进入 `verified`；确认与否定均能驱动 Controller 继续。
  - 产出: approval/verification UI、对应 API 和浏览器级手工验收脚本。

- [ ] **S5.3**: 实现时间线到 Hex、diff、artifact 的双向导航
  - 验收: 点击补丁事件可跳到正确绝对偏移并高亮修改字节；点击 diff 可查看完整差异；artifact 丢失时显示可恢复错误而非空白。
  - 产出: 导航状态、diff 详情视图、artifact 下载入口。

---

## M6: 报告、知识固化与基准评估

**目标**: 将经过验证的轨迹转化为可复现研究资产，并用真实指标证明自主闭环的价值。
**状态**: ⬚ 待开始

### 步骤

- [ ] **S6.1**: 从轨迹确定性生成实验 Markdown
  - 验收: 对同一轨迹重复生成内容一致；报告包含存档指纹、假设、补丁、diff、验证步骤、结果、证据等级和轨迹回链。
  - 产出: `webapp/research/reporting.py`、报告模板、golden-file 测试。

- [ ] **S6.2**: 实现带研究标记的知识库幂等 upsert
  - 验收: 只有 `confirmed` 或 `verified` 可进入知识库；相同 `research_id` 重试不产生重复条目；知识条目和轨迹可以双向定位。
  - 产出: `webapp/research/knowledge.py`、知识标记格式和测试。

- [ ] **S6.3**: 建立 MHXX 金钱字段端到端 benchmark
  - 验收: 从目标创建到生成验证任务全流程自动运行；记录工具调用数、耗时、人工动作数、候选收敛过程和最终报告；非法固化测试保持失败。
  - 产出: `tests/benchmarks/funds_offset/`、可重复 benchmark 命令和基线结果。

- [ ] **S6.4**: 完成运行文档、演示脚本和发布门禁
  - 验收: 新环境按 README 可在 10 分钟内跑通 benchmark；`python -m unittest discover -s tests -p 'test_*.py'` 全部通过；现有存档加载、Hex、补丁、diff、实验和知识接口无回归。
  - 产出: README 更新、演示步骤、API 文档、发布检查清单。

---

## 发布门槛

MVP 只有同时满足以下条件才算完成：

1. 用户只输入研究目标和必要样本，Controller 可以自主推进至第一次审批或人工验证。
2. 所有系统结论都能定位到不可变证据 artifact 和存档指纹。
3. 任何高风险动作都不能绕过 Policy。
4. 重启、请求重试和多标签页不会导致重复副作用或研究串线。
5. MHXX 金钱字段 benchmark 能稳定复现，并展示相较手工流程减少的人工步骤。

## 推荐节奏

- **M1–M2**：建立可信状态和恢复基础，完成后即可单独发布“可审计研究轨迹”。
- **M3**：形成第一个直接用户价值——自动缩小候选字段。
- **M4**：形成真正的自主性，是产品定位成立的关键里程碑。
- **M5–M6**：将能力转化为可用产品和可证明结果。

在单人全职投入下，建议按 6–8 周规划；若以业余时间推进，应按里程碑交付，不以自然周承诺范围。

---

## 变更日志

| 时间 | 操作 | 说明 |
|------|------|------|
| 2026-08-22 13:53 | 创建 | 初始路线图生成；因工作区禁止创建 `.Codex/roadmaps/`，路线图存放于 `docs/`。 |
