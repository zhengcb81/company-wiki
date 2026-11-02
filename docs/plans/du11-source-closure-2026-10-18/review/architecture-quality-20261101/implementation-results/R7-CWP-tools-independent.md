# R7 CWP G1/G2 与工具独立审查

**PASS（最终冻结67文件）**：先独审 CWP G1/G2 的21文件与工具30文件，再追加 G3/G4/G5/末端consumer 的16文件增量。未发现本范围 P1/P2。不是全仓 CI 或真实 H1/摘要/缓存恢复/RF 采用通过。

独审由 `/root/rectify_recipe` 执行，未审自己的 RF 实现，未修改被审源码。第一阶段前后两次 SHA 校验全部相同：core 21/21（manifest 文件 SHA `cd2ae9d5abd15760fb4564f2125e48bc0ac4937a5b3a3e680fe4a0e36c45e01a`）；工具 30/30（manifest SHA `1dc7488c5fb8a89b0c0da15ab94097f2b177167789972125d227f7d29ea52e91`）。逐路径 SHA 与两轮独立测试源码/JUnit/控制台原文见同名 JSON。

## 第一阶段：原51文件独立检查

- >1.3M 完整 bundle 与 100 层合法结构经 typed selection、真实 verify 组装、canonical JSON、bound-bundle 验真，原 source/ref/span/group 内容不丢。删除必需 selection 或改动真实 artifact 字节仍拒绝。
- >旧大小阈值、100 层的 capture receipt 不因为表示体积失败；错误源 SHA、实际响应字节、NaN 费用仍拒绝。
- 新组合的坏 metadata/坏派生 cache 在自动发现中跳过并尝试后续好候选；显式坏 pin 仍拒。此处 dependency proof 与 transport 返回显式 stub，只签自动/显式错误语义，不冒原件读取 E2E。
- current source/as-of/SHA、未知 reservation 与真实 I/O 错误均原样抛出，不变成无费用的新运行许可。
- 在独立 SQLite/artifact store 上真实 prepare 成功后，capture 报错或 checkpoint 成功而 event 真 I/O 失败，均只调用 owner 一次，返回 prepared 原结果；明确 incomplete、event_saved=false，不伪造 activation 或已保存观察。
- 真实双流 child 各 >150k：日志模式保尾部和累计量，exit23 仍红；真实 deadline 回收 PID；默认 payload 模式仍按实际输出预算拒绝，不被 log_tail 全局放松。
- 当前真实仓的 dirty 状态只记录，不阻断正确 HEAD/runtime；错显式 HEAD、错导入根仍拒。Git status/branch 观察失败只显示 unknown，单次 status，不伪 clean。

## 实际结果与审查边界

新增 13 场景首次 **10P3F / 8.94s**。三项都是本审查夹具问题：实际 payload 1.21M 却断言大于 1.3M；两项把 CatalogStore 当成有 `.close()` 的持久连接 owner。已保留原失败与原源码，改为足够大的合法资料和真实 store API 后，仅这三个定点 **3P / 5.10s**；被审产品源码全程未改。不能合称一次“13P”运行。

实际命令使用正常 `C:/Miniconda/python.exe -B -X utf8`、明确短 owned basetemp，独立测试关闭 socket、dotenv、LLM。完整重放脚本在 JSON `raw_evidence.test_review.py.content`，历史第一次脚本也保留；只生成合成资料和临时 SQLite，未读取真实公司原件、凭证、调用下载/模型或运行 211/325 全组。

低层 JSON tree 的迭代 type/cycle/nonfinite/copy/freeze 没有另加层数许可；源字段、引用和实际资源合同仍归原 owner。自动候选容错只在发现边界，不能变成显式 pin 或原件失败吞掉。工具观察失败不污染已完成 owner，但也不声称观察成功。HTTP adapter 的真实读取/token/timeout 预算没有被此报告当成冗余表示门。该阶段不签当时尚未交付的 G3/G4/G5；下面最终增量段另绑定其版本，未用旧收据冒签。

## 最终16文件增量（同一大节点）

最终 core manifest SHA `df0f963258d0805657cf79fc918fa130a007d191eae21912a7465a16347d0ca4`，`delivery_files_sha256` 37项；原21项从未变化。新16项只作增量审，不重跑前面13场景或51文件域。最终全部 core37＋工具30＝67实际文件 SHA 与两份冻结清单相同。原21＋30在第一阶段有前/后两次实际SHA；新增16按交付冻结声明读审，增量结束后核全部67实际SHA，不声称运行内存不可变证明。

新增 **12P / 15.79s，一次运行**，`test_delta.py`/JUnit/控制台原文在 JSON：

- 同unit中，肯定issuer但认证未完成、conditional foreign supplier 两类句子×两顺序：known-only 与 mixed 的关系属性和真实 binding 数完全相同；unknown-only 没有 evidence；原引用完整保留、processing=false/partial，不把未证部分变已完成事实。
- 隔离 SourceCatalog 的真实 TXT 原文通过 combined owner：实读与 metadata 各一次，禁止上层再 open/describe；改动该自有合成原文字节仍由真实 SourceVersionReader 拒绝。
- 5001 导航、70 连续真实层级、长原始标题可完整处理，实际同一 WorkBudget 计费。80个真实 plan key、显式120页/100请求可用；重复同scope/page不重复花页/请求，未知key仍拒绝。
- 在完成windows后的材料预扣边界让同一 account 用尽，完整prefix和canonical keys原样保留，prepare/plan明确partial。零账户在 spy Sequence 成员遍历前停止，不能复制/验证大量材料后才说耗尽。
- 430任务真实摘要handler（纯local modelstub）到公开 persisted parser，>32KiB execution完整通过，改实际task binding仍拒绝。未调用收费模型，不冒摘要经济正确性。

独审共25个新增场景为增量覆盖：第一轮10P3夹具F、只修夹具复验3P，再独立增量12P；不是一轮25P。没有重325/211/94全组，没有改任何作者源码、配置、原件或Git。下一步仅ROOT正常发布与既有CI；真实H1、正式摘要/cache/RF采用仍按主PWF。

## 清理

Owned `C:/Users/郑曾波/Projects/company-wiki/tmp/r7rev` 创建前已断言 absent。全部脚本/日志/JUnit 归档到 JSON 后，核绝对 parent containment、root/后代无 reparse，仅删除该独立目录：30 文件 / 1,795,103 字节，exists_after=false，已恢复初始 absent。收据见 JSON cleanup；未清理他人或无法归属的历史缓存，未把 pytest tmp_path 当自动恢复。
