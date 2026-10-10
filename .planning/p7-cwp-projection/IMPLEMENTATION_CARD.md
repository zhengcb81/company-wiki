# P7-CWP-PROJECTION：JSON 投影确定性、不可变快照与旧版本回放

**可以立即开工。**这是新增 source 叶模块责任包，上一批 M3-JSON 已验收，不重新施工整个 parser/AUTO。只在下面指定的工作目录实施。

## 0. 独立上下文与启动

- 项目：company-wiki。
- 工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/p7/cwp`
- 分支：`codex/p7-cwp-projection-identity`
- base：`f8956d299b52849a4beb06e4071816ec72ddc6a3`
- 唯一 PWF：该工作目录的 `.planning/p7-cwp-projection/`，已放入三文档和本卡同内容副本。
- 阅读：本仓 AGENTS、本卡、自己 PWF；如需上游细节，只读 `docs/plans/cross-market-rf-e2e-2026-10-08/phase6/main_auto_official_json/IMPLEMENTATION.md` 和 `m3_acceptance_2026-10-10/ACCEPTANCE.md`。不改它们。

```powershell
Set-Location -LiteralPath 'C:/Users/郑曾波/Projects/_harness_worktrees/p7/cwp'
$env:PWF_PLAN_ROOT = (Get-Location).Path
$env:PLAN_ID = 'p7-cwp-projection'
& 'C:/Users/郑曾波/.agents/skills/planning-with-files/scripts/resolve-plan-dir.ps1'
```

解析结果必须为本卡 PWF。核对实际 branch/base 与工作目录；新增的本卡启动文档有据可查，除此之外如有其他 owner 改动，保留并报告，不 reset/stash 全树。

工作树已有仅含本卡启动文档的 bootstrap commit；base是源码基线（HEAD祖先），不要求HEAD与base相等，不reset丢掉启动PWF。工作树源码未施工；按自己的PWF执行M1。独立目录内的 `INTERFACES.md`、`HANDOFF_FORMAT.md`、`handoff.schema.json` 和合成example已配齐，相对路径从本卡PWF解释。

## 1. 已有实证与根因

独立纯内存调查证明：同合法两页集合正序/倒序均 complete，但投影 SHA 为 bd857979…/76368146…；枚举顺序进入身份，会重复生成摘要。`SourceProjection` 浅 frozen，修改 issuer 成功且旧 SHA 不变；to_dict 对 coverage/records 等嵌套对象浅复制。span producer version 还写死 1.0.1。

根因是投影构造和快照所有权，并非下载或授权。解决通用问题，不按公司、record36395 或固定来源做 if。此包不证明 AUTO 或真实预测完成。

## 2. 排他写集

允许：

- `src/company_wiki/source_catalog/official_json_projection.py`
- 如需要，新增 `src/company_wiki/source_catalog/official_json_snapshot.py`，只服务此模块。
- 新测试 `tests/unit/test_p7_official_projection_identity.py`、`tests/integration/test_p7_official_projection_compatibility.py`，专属小合成 fixtures。
- `.planning/p7-cwp-projection/**`。

禁止：automation 全部源码、source reader、公共/official CLI、official_json_structure/layout/import、subject/schema/canonical writer、旧共享测试、config/raw/生产DB、旧投影/sealed 报告、安装副本、其他仓。共享测试可以运行，不能改 golden/删断言凑绿。MAIN 独占 AUTO subject/view/store/模型/CLI，外包不接线。

## 3. 固定输入输出接口

现有 build_source_projection、build_projection_from_refs、projection_from_dict、persist/load/replay_projection、build_projection_export 的旧位置/函数/参数/返回 DTO 保留。

在两个 builder 新增 keyword-only `projection_version="1.0.1"`，显式 `"1.0.2"` 为 canonical 新算法；不改变默认。SourceRef2.0、source-projection-ref/1、export/1 字段原义不改。

| 版本 | 构造与回放 |
|---|---|
| producer cwp_official_json/1.0.1 | 保留原页输入顺序和原算法；旧字节/ID/SHA load→replay→export 不变 |
| producer cwp_official_json/1.0.2（opt-in） | 同一合法页集合规范顺序，稳定身份；结构 parser 仍1.0.1、layout仍1.0.0，原字段 pointer/byte 范围不变 |
| 旧 structure1.0.0或未知 producer | 明确 unsupported，不悄悄用新算法解释；原件仍可读取 |

新构造优先按可靠声明页号排序；重复/不可靠页保持真实诊断，以母页 SHA 作稳定 tie-break，不猜缺页、不选冲突赢家凑完整。页内真实 record/字段顺序不重排。load/replay 从封存 producer 分派，不从当前默认猜。

对象隔离全部输入和输出的嵌套可变容器；内部深冻结或等价隔离所有权。to_dict 仍返回普通、独立可修改的 JSON dict/list。不能用 MappingProxy 直接泄漏到 JSON serializer。persist 校验 payload/hash/ID 一致，失配明确拒绝，不自动改 hash。span 记录实际 producer version；真实母页语义验证沿 replay 的 source 边界，不每个 helper 再读所有原件。

MAIN 现在继续旧接口实施 AUTO，完成后仅显式选择新版本；双方不互等、不改对方文件。

## 4. TDD 和三个大节点

### M1：接口与责任 RED

记录基线、写最小失败测试并保存真实 argv/exit/log。优先：两页逆序、三页全部排列的 canonical 身份；输入/to_dict/issuer/coverage/record 深层修改；固定旧1.0.1 golden。测试为契约，不镜像具体排序实现。

### M2：共同实现与集中 GREEN

覆盖：

1. 新算法同页集合 ID/payload/export 一致；旧算法固定 ID 不变。
2. 多页同 pointer 各绑自身母 SHA；第二页变化、role/time/locator 伪造，即使重算 hash 也不能 replay。
3. 缺页/重复页/metadata冲突/重叠ID/record冲突/非法current仍 partial；保留所有诊断。
4. 同页 A/B 公司不同投影、正确筛选；错 issuer 无公司业务证据。
5. 所有输入/输出/对象嵌套修改都不污染 hash 或下次 export/replay。
6. 旧1.0.1 load/replay/export；旧1.0.0仍unsupported；未知新版本不降级。
7. repeated canonical persist 仅一份小派生，raw一份；不保存每家公司整页副本。

运行新两测试文件，再集中运行既有：

```text
tests/unit/test_m3_official_json_parser.py
tests/contract/test_m3_official_json_contract.py
tests/integration/test_m3_official_json_projection.py
tests/integration/test_m3_official_json_acceptance.py
```

命令采用 `python -X utf8 -B -m pytest ...`。CWP 既有 pytest timeout 配置需插件；若禁 autoload，显式启用 pytest_timeout，不修改项目配置掩盖缺插件。改动模块 Ruff/mypy 沿既有标准，不扩大为新全仓门。

### M3：隔离 E2E、独立大节点复核、交接

真实 source import/2→新 builder→persist→catalog close/reopen→load→replay→export，两个 declared layout、多issuer、两页均覆盖。使用自己的 TEMP 和 catalog；记录原始 bytes/SHA、ID、producer/span版本、文件数量/体积；末尾恢复测试目录原状。至少保留旧 fixture，不复制整个86页/资料湖。无真实下载、无LLM。独立 agent 复核顺序/深冻结/旧回放三不变量即可，不逐小步骤签收。

## 5. 提交与交接

正常 hooks commit；有 origin 可推自己的分支，禁止推 master/merge主线。exact HEAD CI如未触发明确记录 not_triggered，由MAIN合后验，不伪报绿。禁止no-verify。

自己的 PWF 中交 HANDOFF.md + handoff.json，格式见总卡 INTERFACES/HANDOFF_FORMAT。列实际diff、新旧API/版本、RED/GREEN/E2E日志、旧原字节不变、TEMP恢复、0 external provider/model/收费、安装候选空、未解决限制。证据目录每次新建短名称，独占写，不覆盖旧 attempt。

**完成范围：** source构造、存储与回放兼容。MAIN负责 opt-in、AUTO A/B subject、generation、publish/read/恢复、定点安装及真实公司研究；不要将这些待办写为本卡PASS。
