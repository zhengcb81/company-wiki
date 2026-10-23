# W11 ROOT integration：实现已冻结，等待独立终审

## 版本与结果

最终6个源码/测试文件的实际字节、LF规范化SHA及母HEAD已冻结在 `handoff.json`。作者4文件接入前，母内容逐一证实等于a2f99db6公共基线，未覆盖主线新改动。作者工区始终只读。

- 初始中性RED：13例 **10F/3P/0E，2.78s**。原失败和源码冻结见 `neutral-red.*`。
- 首次扩展控制：22例 **1F/21P**，发现无效`@graph`结构缺少unknown诊断；已同根因修复。`first-green.*`是历史文件名，实际是失败证据，不作为通过收据。
- 完整关联套件迁移前：**120P/54.91s**。
- 最终实际路径：**120P/50.91s**，包含作者原62+36、ROOT普通unit20、真实本地pages CLI2。见 `final-ci-split-tests.txt/xml`。
- 最终6文件Ruff通过；2份产品源码focused mypy为0。未跑全仓重门、未stage/commit/push。

## 共用根修

1. 条目容器一次选最近article/li/tr，再保持单链接约束；不从更宽祖先借用发布日期，div仍只允许标题回补。修复嵌套li/tr标题、日期、未来排除和无后缀材料恢复，不针对公司写分支。
2. 对application/ld+json仅做有界结构观察，绝不生成/抓取材料URL或执行JS。明确未处理文档声明给`embedded_document_unresolved`；坏/过大/过深/未检查结构给`embedded_data_unresolved`并保持partial。普通Event/Organization无其他限制时仍checked_index_only。每页32脚本、每脚本65536字节/128节点/8层是观察范围，超出保留未知，既有可见anchor继续处理。
3. 20个纯解析回归已移入 `tests/unit/test_official_discovery_scope.py`，普通CI能捕获原10F类问题；2个真实CLI案例留 `tests/integration/test_official_discovery_root_scope.py`。迁移前后原函数/断言AST完全相同，未复制22例两份，未放宽断言。

## 合并边界与空间

作者相对a2f99db6实际45路径：4产品、3自有计划、37 delivery、1开工指针。delivery实占 **792942B/37文件**，Git blob769816B；作者声称的781574B是较早计数，以本次实测为准。无原始PDF/HTML body副本。本次只向母导入4个产品/测试文件和ROOT独占小收据，未复制整套作者PWF/delivery；详 `delivery-footprint.json`。

作者开工指针确切为 **`C:/Users/郑曾波/Projects/company-wiki-r1-source-recovery/START_HERE.md`**，支线相对路径`START_HERE.md`。真实ancestry合并时不可把它提升为母入口，应保留母 `docs/plans/du11-source-closure-2026-10-18/CURRENT_STATUS.md` 的唯一入口。ROOT可三方整合真实作者分支保留ancestry，同时保留本ROOT根修；不能整树替换旧工区。

新预算/resource_budget及narrative/cache5份保护文件均规范化匹配ab95027b；不回退为卡片历史2M额度。仍按当前10M/$20和公司软目标。本离线施工无外网、模型、下载或原件读写，没有新权限/授权状态。

## 清理与交回

所有本次pytest临时根均恢复不存在；显式pytest scratch3533B和私有mypy cache约13.46MB在进程结束后核绝对路径精确删除。未清理历史目录或作者资料。清理收据见 `cleanup-intermediate.json` 和 `handoff.json`。

**实现/测试/报告至此停写，等待ROOT独立终审。** ROOT接手共享PWF、普通commit/push与真实ancestry合并；本节点不等于真实IR原件已恢复、完整站点覆盖或公司审查通过。原486789B正文缺失限制继续保留。
