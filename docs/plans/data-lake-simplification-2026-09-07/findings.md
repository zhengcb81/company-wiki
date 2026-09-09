# 诊断发现

先分离三个问题：文件能否读取、文档内容能否对外发送、开发变更怎样验收。它们不应被一个root kind或一个accepted状态绑在一起。待当前代码核实。

## 已核实配置与初始实现

- 生产config schema1.0，四root company_raw/dayu_portfolio/dropbox_stock/future_lake全部privacy_class=public；reusable_root_kinds含company_raw/dayu_portfolio/directory，覆盖四root。不能说“Dropbox目前默认私有不能用”。priority分别10/20/30/40，future_lake额外声明adapter/read_only/reusable。
- resolver按root.kind生成可复用root集合；之后仅从is_canonical locations检查。全局选副本与请求可用性耦合，仍是物理位置逻辑泄漏点。
- resolver缺runtime_policy默认v1+legacy bridge；这属于迁移兼容复杂度，不是虚拟数据湖本身需要。
- 当前HEAD wiki5c4fa301、filing89c8bdb、revenue81553f13；未沿用9/6为当前。CodeGraph定位到resolver但代码段/行号有明显滞后，使用已定位文件当前正文；猜测root_policy.py/schema.py不存在，改用文件清单，不重试猜路径。

## 下游和抽象泄漏（独立探索初步回传）

- filing当前已取消独立allowed_handle_roots配置，不能沿用“现在维护两份路径白名单”作为精确现状；但无policy_export仍回退companies，需区分已修与兼容残留。
- revenue仍读canonical_path并独立全文件hash，把location_id/绝对路径记入trace；有内容身份抽象，但消费未完全隔离物理存储。
- policy.py文档称单一权限真源，实际export的per-root优先语义与resolver仅kind判断不同。应一处能力决策，多处校验同一结果，不各自实现规则。
- SourceCatalog已有lazy只读reader和写store区分，是应保留的简化基础；scan普通dry-run默认v1而实际scan可从snapshot取v2，增加诊断/生产不一致与迁移状态负担。

## 虚拟化基础与额外复杂性

- store.py的sources以content_sha256唯一；documents与locations分表，locations持有root/relative/absolute path，artifacts/evidence另表。不是完全没有统一数据湖，不宜重写为全新分布式架构。
- service._annotate_locations按root_priority/root_id/relative_path/location_id选canonical；resolver._handle只查该canonical是否is_file，不在这里尝试健康同内容副本。优先级本来可只是I/O偏好，却影响是否能返回文档。
- scanner.py:1038以root.priority控制metadata更新（还有完整性补丁），把物理存储偏好和语义可信度耦合。应按事实来源/质量处理冲突，不以“在哪个文件夹”决定真伪。
- 运行snapshot：v2_resolve_active=true/resolve_shadow=true/scan_shadow=true/persist_assertions=true，v2_bundle_active=false，legacy_bridge_enabled=false；epoch及cohort仍canary-2026-08-10。配置本体schema1.0与多阶段开关并存，不能称纯v2或纯v1；无snapshot构造还默认v1/bridge。
- read_only默认true适用于所有RootSpec；源文件只读与统一可读取完全兼容，不应通过让所有root可写来“权限平等”。
- 文件清单猜测store_queries.py/query.py不存在，已使用具体service/store文件，未运行产品。CodeGraph结构定位有用但本轮精确行号以当前文件为准。
