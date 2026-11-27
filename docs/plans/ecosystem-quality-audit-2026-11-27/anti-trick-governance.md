# 反偷懒、反伪解耦与架构保真治理规范（Anti-Trick Governance Spec）

> **用途**　下列 AP/AT/B 编号供各仓选择与本次改动有关的检查，质量判断以实际行为、职责边界和公开协议为准。
> **状态**　S6 实施中。首批分工与验收以 [实施分工和验收](task_plan.md#实施分工和验收) 为准。

---

## 一、历史实证的十大“模型偷懒 / 伪解耦小技巧”黑名单（AP-01 至 AP-10）

下表来自基线审计。静态匹配提供复查位置；结合实际调用、公开协议和行为用例确认影响。

| 编号 | 反模式（小技巧） | 本项目实证案例（真实教训） | 为何属于伪解耦 / 偷懒 | 唯一合法替代方案 |
|---|---|---|---|---|
| **AP-01** | **私有改名公开（Alias Laundering）** | StockQA `quick_scan_work_store.py:6901-7085` 将 17 个底层 `_validate_schema` / `_reserve_budget_attempt_tx` 等直接写 `api_work_store_* = _*` 挂到公共面，还复制了两份 `MODULE_API_PROTOCOL`。 | 耦合度 0 减少，反而把内部 SQL 事务细节永久固化成公开 API。 | 拆分出独立的领域 Repository，消费方只调用高层领域用例接口，删除底层私有别名。 |
| **AP-02** | **`lambda` / `invoke(*args, **kwargs)` 闭包遮罩** | Dashboard `service.py:132-204` 用 37 个单行 `lambda` 包装 `self.<method>` 塞入 `OperationBindings`。 | 仅擦除 `.__self__` 骗过反射检查，`fn.__closure__` 仍死绑同一个 629 行巨石 `DashboardService`。 | 解散巨石服务为独立构造注入的用例类（如 `ScreenEvaluator`），组合根直接装配。 |
| **AP-03** | **继承写类 + `__getattribute__` 黑名单封写** | StockQA `ReadOnlyWorkView(QuickScanWorkStore)` (`quick_scan_refresh_inspect.py:234-244`) 继承 7,085 行写类再用字符串前缀过滤 SQL。 | 违背里氏替换，底层 schema/连接仍全暴露，一旦漏列写方法即击穿只读保证。 | 组合独立 `ReadOnlySQLiteEngine`（`mode=ro` + `PRAGMA query_only=ON`）注入只读查询仓储。 |
| **AP-04** | **子类化 Store 仅覆写私有 `_connect()`** | StockWiki `security_id_normalization_store.py:79-95` 与 `public_company_assessments.py:233-257` 建 `_ReadStore`/`_ReadOnlyObservationStore` 在外部拼原生 SQL。 | 外部模块仍强耦合底层表名/列名和连接生命周期。 | 在 Store 所在存储包公开显式只读仓储接口（`EntityReadRepository` 等），外部零 SQL。 |
| **AP-05** | **`WeakKeyDictionary` 隐身句柄 + 全局 `ContextVar` 暗度陈仓** | StockQA `_quick_scan_owner_refresh_port.py` 用全局 `WeakKeyDictionary` 藏具体对象；`quick_scan_work_transport.py:521` 用 9 个模块级 `ContextVar` 传权限。 | 用隐式全局状态替代显式依赖图，使调用链与并发生命周期不可推断。 | 用不可变 `DispatchContext` dataclass 通过函数/构造函数参数显式传递。 |
| **AP-06** | **函数体延迟导入 + 回调反转 / `E402` 重导出 / `sys.modules` 垫片** | 全生态 2,960+ 处函数体延迟导入（CWP 1,706、StockQA 384、IQS 280、StockWiki 244、RF 148）；RF `revenue_core.py:481` 靠回调+底部 `E402`；IQS 145 个 `sys.modules[__name__]` 垫片。 | 运行期循环依赖与双向耦合原封不动，仅避免 `ImportError`。 | 抽取底层纯值/契约叶子模块 + 依赖倒置（高层依赖低层 `Protocol`）+ 正式 PEP 621 打包。 |
| **AP-07** | **扫描器只测 `tmp_path` 不测真实生产源码** | CWP `test_layer_public_boundaries.py:379-395` 只在 5 文件 `tmp_path` 测 `runtime_import_cycles()`，从未对 `src/company_wiki` 断言（放行 18 个生产环）。 | 门禁形同虚设，生产源码永远不会变红。 | 门禁测试必须对真实生产根 `rglob("*.py")` 强制断言。 |
| **AP-08** | **白名单膨胀 / 改名续命 / 只扫 4 个文件** | CWP `_LEGACY_EDGES` 改名 `_COMPATIBILITY_PORTS` 还从 6 条涨到 8 条；StockQA `STORE_SQL_ADAPTERS` 豁免 21 文件；FF/IQS 边界测试仅硬编码扫 4–6 个文件。 | 每遇阻碍就扩白名单，架构腐化永不收敛。 | 豁免表实施严格单调递减棘轮（`ratchet`），禁止新增条目、禁止改名绕过，扫描器必覆盖 `rglob("*.py")`。 |
| **AP-09** | **樱桃采摘 CI 清单 / 内存 Mock 冒充真实 E2E / 锁死单 OS CI** | 9/12 仓硬编码 CI 测试清单跳过数千用例；MC `test_ci_workflow_config.py:79` 测试禁止加 Windows CI；ET/RF/StockQA/MC 用内存 `Mock()`/`FakeStageRunner`/`load_config` 劫持替代真实子进程与 TCP。 | 本地自测绿、CI 假绿，真实跨进程/TCP/Windows 故障照样上线。 | CI 必须由 pytest 自动发现全部非 `live` 用例 + Ubuntu/Windows 双矩阵；E2E 必须走真实子进程 + 本地 `127.0.0.1:0` HTTP 替身。 |
| **AP-10** | **局部试点冒充全仓闭环 / 生产代码混入测试替身与私有测试参数** | S2 仅改 1 个试点入口就宣称闭环（其余 11–44 个入口零日志）；ET 公开 `main()` 挂 5–9 个 `_retrieval_*` 私有参数；RF `rf_job_facade.py` 嵌 `FakeStageRunner`。 | 遗留大片未覆盖死角并污染生产接口。 | 强制 100% 入口清单清点核销；测试替身严格隔离在 `tests/doubles/`，经组合根依赖注入。 |

---

## 架构设计和验证

### 边界设计

Phase 3 和其他改变公开协议的卡复用[逐仓蓝图](module-blueprints.md)。新增或改变边界时，把下列与本次有关的内容写入原卡；跨仓接口取舍在该节点评审。止血卡可用已有故障用例开工。

设计时需要回答的事项包括：
1. **目标包结构与单向 DAG 图**：列出每个新/保留文件的单句职责与允许依赖边表（禁止向上依赖、禁止跨子包内部导入）。
2. **端口职责**　列出受影响的操作与 DTO，让调用者能通过窄接口替换实现。
3. **删除与瘦身账单（Deletion & Shrink Ledger）**：明确列出将被**删除**的文件、别名、闭包、`sys.path`/`sys.modules` 垫片、白名单条目与测试替身，以及目标巨石文件的精确行数瘦身目标（如 `quick_scan_work_store.py: 7,085 LOC → ≤ 450 LOC`）。
4. **行为解耦证明设计（B-01 / B-02 对应）**：明确写出哪些低层包将用 `sys.meta_path` 阻断导入验证，哪些上层消费者将用“最小 3 方法 `SimpleNamespace` 纯协议替身”验证。
5. **全入口清单（100% Inventory）**：列出该仓全部 CLI / HTTP / Worker / Scheduler / `feedback_owner` 入口，逐项标明日志与错误边界落点（防止只改 1 个试点入口）。
6. **兼容与回退边界**：明确如何保持既有对外 CLI 参数、wire JSON schema、原始数据与付费台账零破坏。

---

### 第二层：不可造假的机械门禁（12 项静态 AST/Meta 门禁 + 4 项运行时行为证明）

在 **Phase 1 第一个任务卡（P1-00）** 即产出标准化的零外部依赖门禁脚本规范 `anti_trick_gate.py`（各仓落地到本仓 `tests/contract/test_anti_trick_gates.py` 并由 CI 强制运行），实现**先立不可绕过的法网，再做 Phase 2–5 改造**。

#### A. 12 项静态 AST 与元数据门禁（AT-01 至 AT-12）

| 门禁 ID | 名称 | 机械检测逻辑（覆盖真实生产源码 `rglob("*.py")`） | 通过条件 |
|---|---|---|---|
| **AT-01** | **生产源码零运行时环（Real-Source Tarjan SCC）** | 对生产代码全树构建完整导入图（含顶层导入 + 函数体延迟导入，仅排除 `if TYPE_CHECKING:`），执行 Tarjan SCC。 | 全部已完成解耦模块 SCC 数 = **0**；未启动重构的存量模块锁定 `ratchet` 上限只减不增。 |
| **AT-02** | **禁止私有改名公开（No Alias Laundering）** | AST 检查：（1）模块顶层/类体赋值 `pub = _priv`（如 `api_* = _*`、`validate_schema = _validate_schema`）；（2）单文件内重复定义 `__all__` 或 `MODULE_API_PROTOCOL`；（3）`from mod import _priv as pub`。 | 全仓违规 = **0**。 |
| **AT-03** | **禁止 `lambda` / 透传闭包伪装窄端口** | AST 检查：（1）单次构造函数/字面量内包含 `>= 3` 个仅转发 `self.<m>(...)` 的 `lambda`；（2）以 `def invoke(*args, **kwargs)` 批量包裹隐藏签名。配合运行时检查注入端口的 `inspect.getclosurevars` 不得捕获巨石服务实例。 | 全仓违规 = **0**。 |
| **AT-04** | **禁止写类继承黑名单与 `_connect` 子类覆写** | AST 检查：（1）定义 `__getattribute__`/`__getattr__` 拦截写方法的类继承自 `*Store`/`*Writer`；（2）存储包之外的类继承 `*Store` 并定义 `_connect`/`_read_connect`/`_prepare`。 | 全仓违规 = **0**。 |
| **AT-05** | **禁止 `WeakKeyDictionary` 隐身注册表与业务 `ContextVar`** | AST 检查模块级 `WeakKeyDictionary(...)` 赋值与 `ContextVar(...)` 声明（仅允许白名单内的日志/追踪关联号 `ContextVar`，严禁传递业务权限/预算/存储句柄）。 | 业务 `ContextVar` = **0**；`WeakKeyDictionary` 服务注册表 = **0**。 |
| **AT-06** | **函数体延迟导入严格递减棘轮** | AST 统计函数/方法体内的仓内模块导入数（仅放行显式标注 `# optional-sdk:` 的重型第三方可选依赖如 `fitz`/`docling`/`playwright` 在解析适配边缘懒加载）。 | 已重构模块 = **0**；全仓只减不增。 |
| **AT-07** | **单一存储 Owner 门禁（Zero SQL Bypass）** | 除每个仓在配置文件显式声明的唯一 `storage/`（或 `repositories/`）目录外，AST 禁止出现 `sqlite3.connect`、`.execute("SELECT/INSERT/UPDATE/DELETE...")`、以及 `._connect()`/`._read_connect()`。 | 存储包外直连 SQLite/裸 SQL = **0**（彻底清退 `STORE_SQL_ADAPTERS` 21 文件白名单）。 |
| **AT-08** | **生产与测试绝对隔离 & 打包纯净** | AST 禁止生产代码：（1）`import tests` / `from tests`；（2）`spec_from_file_location` 路径指向 `tests/`；（3）定义 `Fake*`/`Simulated*`/`Stub*` 测试替身类；（4）公开 `main()`/`run()` 签名含 `_` 前缀测试注入形参；（5）已打包模块含 `sys.path.insert` 或 `sys.modules[__name__] =`。 | 全仓违规 = **0**。 |
| **AT-09** | **规模趋势** | 报告触及模块的行数、复杂函数和端口宽度，引导检查职责是否混杂。 | 作为架构审查线索。以职责拆分、依赖方向和替换测试判断，行数不单独阻断。 |
| **AT-10** | **白名单只减不增与反改名 Meta-Gate** | 解析本仓 `ratchet_baseline.json` 与白名单常量（如 `_COMPATIBILITY_PORTS`、`DOMAIN_BUDGET`、`per-file-ignores`），强制条目数 `current <= baseline`；PR diff 检查禁止删除旧白名单变量名后新造同类豁免集合。 | 任何新增豁免或改名绕过直接 CI 失败。 |
| **AT-11** | **硬编码与日志卫生 AST 门禁** | AST + 正则检查生产源码：（1）零个人路径（`C:\Users\`, `/Users/`, `C:/Miniconda`, `~/company-wiki`, `../StockWiki`）；（2）零无前置日志的 `raise ... from None`；（3）`except` 内抛新异常必带 `from exc`；（4）零静默 `except Exception/BaseException: pass|continue|return None/{}/[]/False`；（5）`except` 内 `logger.error/warning` 必带 `exc_info=True`（或用 `logger.exception`）；（6）业务子进程零 `stderr=DEVNULL`；（7）`logging.basicConfig` 禁止绑定 `sys.stdout`；（8）非终端展示型 CLI 零 `print()` 写错误。 | 目标阶段（Phase 2/4）清零；期间严格棘轮防新增。 |
| **AT-12** | **CI 收集完整性 Meta-Gate（杜绝假绿）** | 对比 `pytest --collect-only -q tests/`（排除显式 `@pytest.mark.live`）与 `.github/workflows/*.yml` 实际运行的测试集合，断言覆盖率 = **100%**；同时检查工作流不允许缺失 `windows-latest`（针对含 Windows 语义的仓）。 | 0 个遗漏测试文件；0 条硬编码 `CI_TESTS` 樱桃采摘清单。 |

#### B. 4 项不可作弊的运行时行为解耦与可靠性证明（B-01 至 B-04）

静态规则有可能被诡辩绕过，但以下 4 项**真实进程/运行时隔离证明**从物理执行层面锁死架构质量，任何“小技巧”在它们面前都会立刻崩溃：

1. **B-01：低层纯净性 `sys.meta_path` 阻断导入证明**
   - **做法**：启动独立子进程 `python -c`，在导入任何项目代码之前向 `sys.meta_path[0]` 注入一个阻断器，直接 `raise ImportError("blocked by B-01")` 拦截：所有上层包（如 `automation`/`cli`/`ops`）+ `sqlite3` + `requests` + `urllib.request` + `httpx` + `fitz` + `playwright`。然后导入并运行 `contracts/`、`domain/`、`ports/` 全部核心逻辑。
   - **防作弊威力**：无论用 `api_*` 改名、函数体延迟导入还是 `WeakKeyDictionary`，只要低层暗中依赖上层或 IO 库，运行瞬间报错。

2. **B-02：极简纯协议替身替换证明（Pure-Protocol Substitution Proof）**
   - **做法**：对每个高层编排器/用例/适配器消费者（如 CWP 摘要编排器、RF `CatalogLineage`/计算引擎、StockWiki 评估服务、Dashboard `ops/m*`、StockQA runner、FF `ResolveFilingUseCase`），在测试中**不构造任何真实 Store/Service/Adapter**，只传入一个仅有 **≤ 5 个协议声明方法**的裸对象（如仅实现 `Protocol` 方法的最小 dataclass/SimpleNamespace，严禁继承真实类、严禁带 `_store`/`_catalog`/`_connect`/`_environment` 属性）。
   - **防作弊威力**：彻底击穿 `ReadOnlyWorkView` 继承、`_ReadStore` 子类覆写、`self._fallback._read()`、37 个 `lambda` 绑定巨石、`getattr(x, "_*")` 等一切伪封装技巧。

3. **B-03：空目录 Wheel 洁净安装运行证明（Clean-Room Installed Package Proof）**
   - **做法**：用 `python -m pip wheel --no-deps` 打出真实 `.whl`，安装进干净临时虚拟环境，切换工作目录到一个**完全空的临时目录**（无源码树、无 `PYTHONPATH`、无邻仓目录、无生产配置），执行该包全部 `[project.scripts]` CLI 的 `--help` 与离线契约样例。
   - **防作弊威力**：一次性击毙 `sys.path.insert`、`sys.modules` 垫片、`parents[4]` 相对路径、`CWD` 相对文件名、`tests/` 生产导入、`package-data` 遗漏与未声明依赖。

4. **B-04：真实子进程多故障日志与幂等恢复证明（Real-Process Fault & Log Liveness Proof）**
   - **做法**：以真实 `subprocess.run` / `Popen` 启动每个公开入口，对接本地 `127.0.0.1:0` `ThreadingHTTPServer` 替身，实测 4 类强制场景：
     - （a）带合成凭据（`Authorization: Bearer tok_secret_xyz`、`https://u:p@host`、`sk-1234567890abcdef...`）触发真实深层异常 → 读回本地轮转日志，断言**凭据 0 明文泄露**、**堆栈尾部异常类名与行号完整保留（反头截断）**、`run_id`/`attempt_id`/`code_version` 齐全、`stdout` 机器协议零污染；
     - （b）日志与旁路均不可写时，业务结果、退出码及已有机器输出协议保持可用。若 stderr 本身承载一份结构化回执，通过原约定字段或独立诊断通道留证；以真实消费者解析验证。
     - （c）在派发前和派发后分别强停，从新进程找回原作业。对比恢复前后外部实际调用和费用计数，新增均为 0；未知费用保持待证。
     - （d）Windows 实测本次进程树新增可见控制台窗口数为 0、含 `#`/`%`/260+ 字符路径及双进程并发日志轮转零丢行。

---

### 关键节点独立审查

每个模块首次止血交付、P1-00 工具交付、后续架构边界切换和组合发布均由实施者以外的审查员核验。可按同仓相关变更合并一次审查。用发布基线、候选差异和一个有区分力的反例判断实际行为。已有同版测试记录可以复用；证据缺失、环境相关或合并改变行为时，只补受影响的验证。

审查关注被削弱的有效断言、越权存储、假端口、漏入口、丢失溯源、协议破坏及污染原件等实际风险。静态指标的命中注明位置和影响。结论记录卡号、基线/候选 SHA、命令或现成收据、观察与未决项，一处留档供总控引用。既有独审交接格式可以沿用。下例是大型架构切换可记录的详细字段。

```json
{
  "schema_version": "anti-trick-review-receipt/1",
  "card_id": "P3-01",
  "repo": "StockQAbyLLM",
  "commit_sha": "<40-char git SHA>",
  "blueprint_path": "docs/plans/.../blueprints/P3-01.md",
  "verdict": "ACCEPTED | REJECTED",
  "anti_pattern_audit": {
    "AP-01_no_alias_laundering": "PASS",
    "AP-02_no_lambda_masking": "PASS",
    "AP-03_no_readonly_inheritance_blocklist": "PASS",
    "AP-04_no_store_connect_subclass": "PASS",
    "AP-05_no_weakkey_or_business_contextvar": "PASS",
    "AP-06_no_lazy_import_or_shim_cycles": "PASS",
    "AP-07_real_source_gate_not_tmppath": "PASS",
    "AP-08_ratchet_strictly_decreased": "PASS",
    "AP-09_ci_full_discovery_and_real_e2e": "PASS",
    "AP-10_full_inventory_no_prod_test_hooks": "PASS"
  },
  "before_after_metrics": {
    "runtime_sccs": [1, 0],
    "max_file_loc": [7085, 480],
    "sql_bypass_files": [21, 0],
    "deferred_imports": [384, 0],
    "logged_cli_entries": ["4/15", "15/15"]
  },
  "adversarial_probe_run": "Exact command & observed result proving decoupling/resilience",
  "file_sha256": {},
  "blocking_findings": []
}
```

### 修复与接收

审查发现问题时，记录受影响的行为与复现条件，沿原卡修复并复验差异。保留已经成立的证据。只有遇到跨 owner 决策、真实外部依赖或持续无法推进的问题时，才交总控协调。

完整双平台套件由 Phase 1 发布节点和最终组合节点承担。首批 P0 和 P1-00 分别使用[验收表](task_plan.md#实施分工和验收)；后续按改动选择行为证明。
