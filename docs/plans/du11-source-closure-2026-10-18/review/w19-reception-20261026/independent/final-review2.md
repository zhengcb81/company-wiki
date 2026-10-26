# W19 第二次独立分层终审

**PASS / 0 OPEN（本次实现与离线边界范围）**。官方六值对照仍为范围外 OPEN；不代签发布、精确 CI、C3、cache/RF 或 live API 全面完成。

本轮独立发现并由 ROOT 修复四组共用根因，均有红/绿探针：

| 问题 | 根因与最终行为 |
|---|---|
| P1 离线 replay 伪造 provider 新观察 | 旧 A 在 B 后重算曾令 current/PIT 倒退。现在 replay 不改已有版本 last_checked/观察，新恢复绑定 reader 原 capture 并标顺序未知；A100→B200→replay A 后仍 B200，观察2→2。 |
| P2 缺身份快照异常及提前建库 | service 曾先开 writable DB 再抛缺 snapshot 异常。现在 repository 延迟至身份成功，既有 facade 返回 company_identity_snapshot_unavailable，零 provider 调用、缺省 DB 仍不存在。 |
| P2 legacy 顺序未知却称 current complete | 同秒迁移不能证明 A/B 先后。现在公开 observation_order_verified 并返回 partial/legacy_observation_order_unverified；真实 provider 再确认只新增一次 verified 观察，计数2→3→3，历史 PIT 仍未知。 |
| P2 FF 缺省字段与 CWP 合同漂移 | tuple 默认值后强制 list 曾拒绝合法缺省请求。现在3种省略接受且不补请求字段，8种显式非法值拒绝；实际完整离线链验证双字段省略。 |

原 ABA、同秒更新、未来 coverage 借用三反例均关闭。最终相关21项 pytest 全绿，关键源码/测试执行前后 SHA 一致；此前19项被此轮覆盖，初始73项包含 unit alias 与直接测试重叠，均不相加。PDF既有15项边界测试通过，独立完整 neutral backend 验证共享 budget、绝对 deadline、同 backend select/verify/replay、source/recipe 拒绝，未导入 Docling。AST 正反 self-test及拒绝 httpx/Sina import 的纯模块加载验证通过。FF初始8项静态绿没有替代本轮合同语义反例。

独立实际使用 `.venv/Scripts/python.exe` 运行冻结脚本一次：真实 FF 有界子进程→CWP CLI→冻结新浪 fixture provider。`independent-offline-boundary-v1.json`：36/33/36期、9729行、4049个 numeric JSON pointer 原值核对、12份返回 SourceRef 直接打开；第二次 fetch 与 reuse_only 各0 fixture exchanges。原件/sidecar/config逐字节不变，mode=ro/query_only iterdump逻辑内容不变；初始11,541,954B<16MiB，净变化−4,264,232B；tmp已清理，产品SHA绑定稳定。15次fixture exchanges不是真实HTTP。

SQLite验收设计通过：只把精确 catalog.sqlite3/-wal/-shm 排除出原件字节比较，同时检查只读逻辑dump与零写入CatalogStore行为。WAL checkpoint可改物理hash并回收空间，不等于业务内容变化；空间约束使用实际净增<=0，没有写死0或宽泛排除其他文件。

新增1.2/1.3旧schema两例反证了“财务增表必然阻断旧原件读取”的假设：删全部财务表后，既有SourceRef仍读回同bytes，读取时DB字节不变；财务reuse只返回具名缺表、不写迁移。因此reader.py保持不变，未无据放宽版本声明。

实际产品/测试LF SHA、脚本/收据字节SHA、各反例与复验详见JSON。审查者未改生产实现、配置、原件、作者工区或其他WIP；所有试验写入均属独占短tmp且最终清理，0真实网络/模型/下载。ROOT集中检查和平台mypy另行归属。官方六值不能由冻结第三方源内一致性取代。
