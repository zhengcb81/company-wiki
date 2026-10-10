# Findings — P7-CWP-PROJECTION

本卡完整已复现实证、根因与稳定接口见 IMPLEMENTATION_CARD.md §§1–3；这些是施工起因，不是本卡已经实施的结果。

写集只限本卡；MAIN保留AUTO共同接线/跨仓安装与并线。另两卡物理目录和源码写集不同，不等待它们的新接口。原件/配置/旧证据与其他ownerWIP不改。

环境/工具配置沿项目实际设置，不猜供应商或模型。默认项目provider/model/新增费用均0；外部harness自身推理不冒作项目供应商调用。已有累计USD20/2M与旧unknown保留。

RF历史跟踪约870MB，本次复用干净树避免再复制；不在本卡删除历史.planning。每个真实发现/失败追加于此，不覆盖旧证据。

## 施工期发现（2026-10-10）

1. 既有 M3 消费者契约 `coverage["diagnostics"] == []` 要求冻结列表与 list 相等；深冻结列表实现为 tuple 子类保留 list 相等语义，否则冻结改动破坏旧断言（M2 中真实回归，修复后 138+26 全绿）。
2. `_ref_from_dict` 原用 `isinstance(value, dict)`，冻结后的 parent_source_refs 元素是 _FrozenDict 会被误拒；放宽为 Mapping。
3. 复审发现（minor，已修）：FieldBinding 无 __post_init__，list 型 range 可被调用方原地改写；已加冻结。`_FrozenDict._data` 私属性可达属 Python 不可变对象通用旁路（等价 object.__setattr__），persist/replay 会拒绝漂移对象，保留记录不修。
4. 复审确认 golden df3f65… 与 HEAD（M3 已验收版）内存重放逐字节一致，1.0.1 路径无回归。
5. E2E 首跑脚本 REPO 路径算错（parents[4]），import 了旧安装副本报 TypeError；修正 parents[3] 并加 `company_wiki.__file__` 必须在 worktree src 的断言，防再犯。
