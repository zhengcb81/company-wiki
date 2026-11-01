# R6 B域独审 — 消费者、ROOT测试迁移与候选CI入口

**结论：本次冻结的消费者/测试迁移范围 PASS，未发现需修复的实质 P1/P2。** 可以纳入候选整合；不表示语义 owner、W23 工具、Linux 全域 CI、真实摘要/缓存恢复/RF 采用已完成。

对象：`C:/Users/郑曾波/Projects/company-wiki/tmp/architecture-r2`，分支 `codex/architecture-rectification-r2-20261101`，基线 HEAD `f298a383ff97b406fae27d49a3c50a16fb95dd3d` 的当前未提交改动。独审者 `/root/rectification_review_a` 未参与这9份测试/CI修改，未改作者源码、测试、索引或主PWF。与同名 JSON 一起读取，JSON 绑定 **5份消费者测试＋4份ROOT测试＋1份CI YAML** 的实际 SHA，10/10 对应作者收据且执行后不变。

## 为什么这不是删断言换绿

已逐份对比基线 diff、实际新 owner 和原41RED清单。消费者5文件的 AST `assert` 数依次为 **25→25、4→7、2→5、30→30、64→64**；ROOT4文件为 **47→50、46→47、58→60、22→22**。计数仅作旁证，实质判断如下：

| 范围 | 独审判断 |
|---|---|
| narrative source usability | 只把私有 `import_module` 注入点从历史 DU shim 移至真实 `source_catalog.narrative_decision_inventory`。原公开 `build/current_decision_trace` 仍经兼容入口调用；不同 MIME/实际 matcher、相关模块变化失效、其他 carrier 不误失效、移动安装路径及 CRLF 不变、旧歧义 trace 不复用等断言全部保留。没有为测试新增反向 facade 代理。 |
| 缺 PDF projection | 删除 `raising=False` 幻影 patch，向真实 inventory owner 注入模块缺失/版本缺失，仍要求 PDF 不 complete、HTML 不变。避免在未使用 shim 上新增属性后误以为测到了失败。 |
| native list ancestry | `independent_statement_start` 从真实 `operating_states.relations` 注入 `SourcePageFlow`；unfinished/furniture/terminal/未知列等原断言未变，没有恢复 reading facade 的私有 alias。 |
| canonical exact reference | 测试不再 mock 高层 reader 直接返回/抛错，而只给 `exact_source_version` 一条 row。实际 `CanonicalSourceWriter.source_ref_for_import → query_source_reference` 执行 SHA、active、缺行判断。成功/三个失败均恰好一次 exact(document_id)；无 metadata 搜索或 capture 许可。三个真实失败 cause.reason 分别仍为 `document_not_indexed`、`expected_version_mismatch`、`source_not_active`。窄替身不提供高层API，重新绕回高层路径会失败。 |
| CF3 | 不只测 `_versions` 私有摘要：实际 pipeline → build trace → freeze → `current_reading_decision_matches` 初始 complete/same 必须 True；关系 owner 源字节变动后摘要变且真实 generation cache 检查必须 False。新增源码子模块/不相关 txt/相同字节异路径反控仍在。它验证的是现有 generation 缓存判断入口，不冒称持久Store或付费恢复端到端。 |

原41RED主要因补丁/导入落在重构前私有 owner，不能因此恢复跨层耦合。迁移后没有删除原来的负控、加 skip/xfail、提高额度或改产品源码迎合测试。

## ROOT schema/SQL/offline 改测是否正当

**Schema 3/6 → 8：正当。** 实际 `migrations.py` 的 v7 是 nullable `paid_response_json`，v8 在原 AUTO 库内新增 `narrative_storage_allocations`。旧测试要求“表集合完全不变”已经不符合这项既有架构变更。

新测试仍要求原表全保留，新增表集合**恰好只有这一张**且记录为空；v3 旧事实逐值相同、旧 reservation/job/run 的前缀列不变、新 nullable 列为 None、旧 owner 不凭迁移获得绑定，备份原字节/迁移版本顺序断言也都保留。不是把所有新增表放行。v6 测试继续查 receipt 列存在及 current schema 版本。迁移合同特定的新表名属于合法预期；这与在通用 SQL 注入测试里固定一个跨版本历史表列表不同。

**SQL 注入：正当并更聚焦。** 真实 malicious JSON 写入前拍 `schema_report().tables`，先确认 events 存在，写后 exact 表集合一致，payload 必须逐字 roundtrip。原固定旧 schema 表名集合删除，但“SQL数据不能删表”的行为仍测；schema 是否完整由迁移/inspect 合同负责，没有删安全断言。

**Offline：显式目标 package 修复成立。** 旧 fresh child 可能从宿主 editable 导入主工区而非候选。新 child 使用 `-I`，显式插入当前测试实际 `grammar.__file__` 的 src 祖先；故意污染 PYTHONPATH，仍必须执行双语 inference。下载入口/默认 jieba 初始化被 forbidden，temp/cache 前后空、ambient marker 保留等原断言不变。`parents[3]` 对当前 package 的 `.../src/company_wiki/document_understanding/statement_grammar/__init__.py` 确实指向当前 src；未硬编码用户机器路径或公司。

ROOT已报告正常宿主72域 **72P/28.53s**，sandbox下15个原子写失败由 `os.link` WinError5 解释，不再在 sandbox 重跑这72域，也不改原子提交策略。当前 `R6-ROOT-test-changes.json.host_72_domain` 和 ROOT报告末尾仍写 in progress/待host验证，需用既有实际结果更新；这是文档收口，不应再跑一轮测试。

## CI变更范围

YAML 唯一变化为原 push 分支 `[master]` 增加 **`codex/architecture-*`**。仍是同一 workflow/job，PR master 与原 paths-ignore/并发规则不变；未扩展全部 codex/外包分支，未复制流水线，未删除 lint/mypy/compile/config/full-unit/contracts 或改超时来掩盖失败。目的只是在并线前让总控候选获得原有完整CI；实际候选全域CI结果仍待ROOT验收。

## 独立执行与精确边界

在正常获准宿主 `C:/Miniconda/python.exe -B -X utf8`，使用隔离 env、`-p no:cacheprovider` 和 ROOT自有 tmp，仅补跑：

1. canonical reference 四例；
2. CF3 两例；
3. offline fresh child 一例。

结果 **7P/10.98s**，没有跳过。JUnit全文/逐例结果/命令/env保存在 JSON。没有重跑作者50域、ROOT72域或全仓。

总审查窗口检测到正在施工的 `statement_grammar/__init__.py`、`narrative_source_passage.py` 两份语义源码变化，故不把这7P冒签最终语义冻版。为排除变化恰好使 CF3 cache 反控假绿，只补跑 **CF3真实 generation 比较这一例：1P/4.02s**，在该独立执行窗口绑定的11份相关源码前后 SHA **全部相同**；10份冻结测试/CI文件一直未变。这个窄复验解决了该因果证据的并发疑点，不把语义实现纳入本次签收。

本次首读曾误用候选工区的报告相对路径，发现报告实际由ROOT保存在主工区后改用明确位置；未改文件或回退其他计划，不属于产品故障。主CodeGraph仍有旧实现快照，对本次已知文件的实际 owner 以候选源码核对，没有建立新索引。

## 清理与交接

所有新测试材料只在 `C:/Users/郑曾波/Projects/company-wiki/tmp/r6-consumer-review`。首次 basetemp 长度64触发既有hook重定位到该目录的 `temp/cw-pytest-basetemp`，hook已报告清除；第二次使用长度59的自有目录，无重定位。最终ROOT自有目录整体恢复初始不存在，收据见 JSON。未读取密钥、调用LLM/OCR或付费API、下载/解析原件、写生产库或配置；没有修改作者的语义/W23/其他测试。

**本B域 PASS，STOP。** 下一责任是ROOT冻结并验收语义改动、更新已有host72记录、运行候选精确CI；本独审不提前替这些工作签全域完成。
