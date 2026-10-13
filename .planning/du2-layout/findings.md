# DU2-LAYOUT 发现记录

## 环境事实
- 运行时 Python 3.13.9（Miniconda），PyMuPDF 1.26.7 已装（只读观测字号/几何用）；ruff 0.15.18。
- editable 安装 `company_wiki-0.1.0.pth` 指向**主线 checkout** 的 src，不是本 worktree；
  集中命令 `python -B -X utf8 -m pytest tests/unit/document_understanding_layout_hints -q`
  不带 PYTHONPATH，因此本包测试目录的 conftest.py 先把本 worktree `src` 插到 sys.path[0]，
  否则会 import 到主线安装副本（那里没有本包）。不改安装副本。
- 父包 `src/company_wiki/document_understanding/__init__.py` 按卡片禁令不创建；
  Python 3 隐式命名空间包可正常 `import company_wiki.document_understanding.layout_hints`。
- Windows 进程峰值 RSS：`psapi.GetProcessMemoryInfo` 在本环境返回 0（不可用），
  改用 `kernel32.K32GetProcessMemoryInfo`（ctypes，无新依赖）成功；每个规模起独立子进程取干净峰值。

## 现有前端几何能力（只读调查）
- `document_normalization/{html_parser,docx_parser,pptx_parser}.py`、`parser_adapters/*` 均不产出
  bbox/font_size/font_weight；只有 source_catalog 的 narrative 侧（docling blocks）偶带 bbox。
- 结论：du2-layout-input/1 的 bbox/font 字段需要 ROOT 在前端补采（PDF 走 PyMuPDF span 级、
  HTML 用已有 DOM 几何、PPT 用形状框）；当前生产输入不满足列恢复所需粒度 → needs_upstream。

## 真实原件（sample_manifest.json，SHA 已复核一致）
- hk-annual 名创优品 2024 港股年报（sha 07f4937e0558…，2230253 B）：p12 门店表（MINISO + TOP TOY 两张表），中英双栏。
- cn-equity 恒锋工具 2020 向特定对象发行募集说明书（sha 37f7c62de54b…）：p61 募投概况表(项目/内容两列) + p62 投资计划表(4 列,含"单位：万元")。
- cn-convertible 金禾实业可转债募集说明书（sha 3ce59fde9895…）：p223 6 列募投表 + 备案/环评表跨页续 p224。
- cn-annual 中微公司 2025 年报（sha d64c410832f2…）：p41 叙述页（行内数字负例）。
- cn-ir 万润股份投资者关系活动记录表（sha 221467c15a24…）：本轮未用（本包不含 QA 语义，属 STRUCTURE/FACETS）。

## 实测结构（C 节点，见 c-evidence/c_node_summary.json）
- 名创 p12 span 级：2 表区（置信 high/high）、3 列、header_for+caption_for 齐；无 NEEDS_UPSTREAM_GRANULARITY。
- 名创 p12 整行单格（当前生产式输入）：2 表区 low、**max_columns=0 不虚构列** + 2×NEEDS_UPSTREAM_GRANULARITY，complete=false。
- 恒锋 p61-62 span 级：4 表区（high/high/medium/high）、4 列、header/caption 关系 5 条、**无伪跨页延续**。
- 金禾 p223-224 span 级：3 表区 high、6 列、**1 条 continuation（basis=page_gap=1 + column_alignment）**、
  2 条 LOGICAL_ROW_UNRESOLVED（折行逻辑行诚实 partial）。
- 中微 p41 span 级：**0 表区**（行内数字未变表格；负例成立）。
- 原件只读：4 份原件跑前/跑后 SHA + mtime 完全一致（见 perf_observations.md 同目录记录）。

## 实现过程中发现并修掉的真实缺陷（都是本包内部）
| # | 症状 | 根因 | 修法 |
|---|---|---|---|
| 1 | 所有 unit 都 missing_geometry、零表区 | `contract.parse_observation` 建了 `Page` 却没 append 到 `doc.pages` | 补 `doc.pages.append(page)` |
| 2 | 跨栏页眉把栏切分吃掉（无 lane） | 全宽页脚 unit 覆盖整个 x 区间，扫不到空白间隙 | 栏候选排除页眉/页脚带（上 8%/下 10%） |
| 3 | 稀疏页（每栏 1 个 unit）无栏 | 栏切分要求本页 ≥4 unit | 切分改为**整篇文档**共同学习，`column_lane` 组仍按页产出 |
| 4 | 表区结构对但行 `required_context` 缺表头 | 行上下文只挂了 caption/footnote | 行上下文 = 题注/脚注 + 表头块 unit |
| 5 | 工作预算超限无诊断、无 deferred | 只 `charge` 未回报也未推迟未分析 unit | 超限时发 `WORK_BUDGET_EXCEEDED` 并把未成带 unit 移入 `deferred_unit_ids` |
| 6 | 数量为空文本表（恒锋 p61 概况表）把全部行带当表头 | 表头块无“必须后随数量行”的约束 | 无数量表区最多取首个行带为表头 |
| 7 | 名创门店表表头块识别不出、列置信降级 | 上下文/数量判定按 `band.units` 数而非**格子**数（"截至 12 月 31 日"被切成 5 个 unit） | 上下文/数量判定改用 cells；期间/日期行不算数量 |
| 8 | 跨页页眉/编号小标题混进表区行 | 行带成员未排除 furniture 与编号小标题 | 成员排除 furniture 与编号小标题行带 |
| 9 | 整行单格表（当前生产输入）拿不到粒度诊断 | 原 grid 判定要求整个 run 全对齐，表头碎片行带破坏对齐 | 改为在 run 内提取**对齐子串**（≥3 行带、≥2 含数量）成粒度表区 |
| 10 | "、" 被当句末标点，正常表格行被当正文排除 | 顿号常用于单元格并列词 | 句末标点集合去掉 "、" |
| 11 | 真实用例 assert 拿到正文里的同名数字 | 测试取 `_units_by_text(...)[0]`，正文提及先命中 | 测试遍历全部同名 unit，取真正落在表行里的那个 |

## 错误记录
| 错误 | 尝试 | 解决 |
|---|---|---|
| 误向 pytest.ini 发 write（占位符） | 1 | 被 fs 保护拒绝；此后未再动共享文件 |
| `scratchpad` 目录 EPERM 不可建 | 1 | 改用 `%TEMP%\du2-layout-work\` 放探索脚本，未写入仓内 |
| 测试文件语法错误（多余右括号） | 1 | 修正 `shape()` |
| `ordering.py` 误删换行导致语法错误 | 1 | 修正 |
| `psapi.GetProcessMemoryInfo` 返回 0 | 1 | 换 `K32GetProcessMemoryInfo`（成功） |
| PowerShell 读 UTF-8 .ps1 脚本中文路径乱码 | 1 | 改为逐条内联命令 + `workdir` 参数 |
