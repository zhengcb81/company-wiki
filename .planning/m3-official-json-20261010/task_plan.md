# M3-JSON：官方多公司 JSON 原文、公司投影与公开读取

唯一执行 PWF（接管 W02 seed）。工作树 `C:/Users/郑曾波/.codex/worktrees/m3-official-json-20261010/company-wiki`，branch `codex/m3-official-json-20261010`，base=3c791e3c2a16c12627cc25d0bd8681cc9458e48b。
Seed 原表（W02，保留）：合同与入口调查/结构 parser DTO TDD/公共 import-project-read-export/JSON route 与共享接线交接/本机冻结页与正常 hooks 交付。

目标：一份真实原页，多家公司各自准确消费。通用结构 parser、显式 raw subject、公司投影、公共 import/project/read/export、恢复与兼容。

## Goal

按 official_json_projection.md 施工顺序 1-7 完成；责任测试矩阵全绿；RED→GREEN 证据保存；HANDOFF 三件套 + raw 日志；正常 branch push + 精确 CI 记录。费用/公网/模型 0。

| 阶段 | 状态 | 验收 |
|---|---|---|
| 1 PWF/基线/consumer map | complete | worktree/HEAD/status、原件/config/测试根 SHA；consumer map 与接口例进 findings |
| 2 结构 parser TDD（RED→GREEN） | complete | RFC6901、token/byte/decoded 分开、UTF-8/escape/surrogate/dup key/finite/限额；两声明布局；无公司硬编码（57 单测绿，冻结锚点复现） |
| 3 raw subject/manifest2 + projection DTO TDD | complete | single/multi/unattributed 不伪造 owner；manifest1 严格读不变（26 contract 绿） |
| 4 公共 import/2 + project/read/export | complete | CLI import/project/read/replay/export；共享 raw `_shared`；篡改/错 pointer/错 issuer 拒业务保留 raw（11 集成绿） |
| 5 Q/A 角色与时间语义 | complete | 问题≠公司确认；致辞≠回答；speaker unknown；answer首发未知；三 completeness 分列；多页 pagination partial 诚实（冻结 86 页 24/231/2 + 668,749 bytes 复现） |
| 6 恢复/幂等/预算/兼容 | complete | /2 失败留 capture 可 recover；重复 import/投影幂等；v1 TXT/FMP/manifest1/export2.0 兼容（相关回归 173 绿） |
| 7 MAIN 接线包 + 提交/push/CI + HANDOFF | complete | INTERFACE_CHANGE.md；AUTO patch 建议；handoff.json main_auto_integration=pending；commit+push+CI 见 HANDOFF |

## Next Step

无——本卡工程范围完成。MAIN 大节点接线与三仓真实大节点见 HANDOFF.md remaining。

## Decisions Made

- PWF 根=worktree `.planning/m3-official-json-20261010/`；PLAN_ID=m3-official-json-20261010。
- 新代码放 source_catalog/official_json_*.py（INTERFACES.md M3-JSON 允许 official_json_*）；合同 DTO 放 source_contract（写集内）。
- 测试命名 test_m3_official_json*，分布 tests/unit、tests/contract、tests/integration。
- 冻结页只读引用；集成测试只经公共 importer 在独占 TEMP 落 4 页副本；其余 82 页 + 3 error control 只读验证；未复制整库。
- 共享 raw 位置由存储层决定：`companies/_shared/raw/<kind>/<sha>.json`；scanner `_infer_company` 不会给 `_shared` 命名实体行 → 单公司查询天然不可见，消费走投影。
- `/2` 语法失败/error envelope：staging 保留 + journal failed，不入库；合法但未知布局：入库 + parse_status=unsupported_layout（typed）。
- error envelope 判定：status 数值 ≥400 或声明的 error 字符串字段非空；缺 success 且无 error 信号 = layout_pointer_not_found（不猜）。
- import/2 请求复用既有 staging/`official-source-retained-capture/1`/AcquisitionJournal/result.json 恢复链（_load_retained/_import_retained 按 schema_version 分发；completed 记录附 /2 字段）。

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| 主项目无 W02 目录（只在 worktree untracked） | 1 | seed 从工作树内路径复制 |
| heredoc 追加被 shell 截断损坏 projection 模块 | 1 | Edit 工具重写损坏段，ast.parse 验证 |
| 测试常量转录笔误（d87c…/e19d…） | 1 | 按证据文件 grep 原文修正 |
| cleanup_staged 双删（writer+flow） | 1 | shared commit 传 cleanup_staged=False |
| request_list 破损态 AttributeError（_load_retained .get on list） | 1 | isinstance(request, dict) 守卫 |
| mypy：字面值复用/键窄化/CLI 联合类型 | 1-2 | 重命名 literal_value、assert 窄化、read 分支提前 return |
