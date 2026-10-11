# W06 CWP 跨期来源修复：非作者验收

## 结论和范围

**PASS_SOURCE_SCOPE_FIX_PENDING_ROOT_MATRIX**。本次非作者静态检查及 13 个独立合成公共 API 探针通过，没有发现需要阻止 ROOT 进入原 41 个 FF→ET→CWP CLI 矩阵回放的来源层问题。这不是对尚未完成的矩阵、真实供应商网络或整个项目的完成声明。

验收对象是隔离产品树 `C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-acquisition-scope-root`，产品冻结 SHA：`1a753dd95c8e897891c48ee5e00e47bde0723a21741aae823af9806619ecdc91`。独立核对全部 12 个冻结产品文件及作者 manifest 列出的旧证据；测试前后均与冻结值一致。审查者没有修改这些产品文件，亦没有修改 FF 工具、生产配置、原证据、Git、技能安装副本或共享 PWF。

## 一个集中验收节点

`independent-public.stdout.txt`：**13 passed in 5.13s**；完整命令、受控环境、自有 scratch、前后 SHA 和还原结果在 `independent-public-result.json`。为核对 SEC 原生 parser 与普通 US/PDF 路径的差异，只补跑增强后的 DEI 单条：`sec-native-cross-period.stdout.txt`，**1 passed, 12 deselected in 1.67s**；实际不同原文 FY2023→FY2024 获取和同期零下载通过。全部使用真实 `SourceAcquisitionService.ensure`、`CanonicalSourceWriter.import_staged`、`SourceVersionReader`、来源事实库和扫描器；provider 仅是返回小型合成原文的内存 fixture。没有调用实际 provider 或 LLM，没有读取/继承真实 API 凭证。

| 检查点 | 独立验证 |
| --- | --- |
| 年报跨期 | Beta Systems 的 CN 2022→2023、HK 2025→2026、US 2023→2024 均真实入库新版本；旧原文和 SourceRef 可再次实读，字节不变。 |
| 非年报跨期 | HK 同年 Q1→Q2、半年 H1 跨年均获取正确的新 scope。 |
| 同期复用 | 上述五条向量分别在新旧期执行 `allow_download=False`；每次均 `reused`，发现和获取计数没有增加。 |
| 自动可信事实 | 普通下载经唯一 writer 自动写入 `source-facts`，不是依赖后续修复命令或人工签收。 |
| 历史来源升级 | 旧 writer 的真实成功 journal 与 request/candidate/receipt/原文版本绑定后，仅提升显式 scope；没有提升 publication、filing date 或 title。旧期排除时故意令身份查询和原文重解析报错，仍正常获取新期。 |
| 不可信声明 | 改动历史 journal 的 candidate ID、保留旧 digest 后不能当成功捕获凭据。只有扫描 sidecar 的 `created_by/capture_ready` 声明也不能生成可信事实或自动排除；返回具名 blocked/unavailable 诊断并保持零 provider 调用。 |
| 原文 SHA | 对同期原件注入相同长度的坏字节后拒绝复用；journal 为 `downloaded_new, failed`，没有成功 reuse 记录，provider 计数不变。 |
| 原文事实优先 | 用实际合成 SEC HTML DEI 建立 FY2023/FY 原文事实后，同字节 FY2024 provider 声明被拒绝。来源事实与原文未被改写；真实不同 FY2024 原文经原生解析路径正常获取、随后零下载复用。 |
| 同字节跨 FY | 非 SEC PDF 的相同字节配新 FY 声明被 `canonical_scope_conflict:fiscal_year` 拒绝；第一份 sidecar、事实和原文保持不变。 |
| 事务回滚 | 新注册在事实已写入后注入失败：documents/sources/locations/assertions 全为 0，staging 保留且同一公开 writer 重试成功。退役来源在重新激活之后注入失败：来源、location、事实和原文全部与前态相等，仍 retired。 |

请求、响应和计数逐次写入 `public-api-trace.jsonl`。合成股票名、年度和证券代码有意不同于作者的 Acme golden，避免仅重复作者输入。

## 静态职责检查

1. `canonical_scope.py` 将期次相关性与可信事实来源放在同一来源层。`qualified_source_scope` 只认可已有已验证事实、或绑定 genuine successful journal 的历史捕获；扫描声明是 UNKNOWN。SEC HTML 的实际 DEI 仍由已有原文资格逻辑负责。
2. `local_reconcile.py` 在身份库查询、旧原文重读和 retired restoration 之前排除 `NOT_RELEVANT`。未知身份或字段不会被伪装成“空湖”，其具名诊断保留到无路径 DTO。这是数据质量职责，没有新增人工许可。
3. `canonical_writer.py` 在验 staging SHA/字节/MIME 后生成带版本绑定的捕获事实；已有更强事实只能补缺，不以新 provider 声明覆盖矛盾期次；dedup 不重写第一份 sidecar。
4. 新 writer 的单文件 scoped registration 及事实 callback 位于同一 store coalesced transaction 内；重新激活在事实成功之后，失败会回滚。在本次两个后置故障探针中已实测此边界。未把该保证扩大为任意多文件、跨 250-operation batch 的原子保证。
5. `acquisition_service.py` 的同期 REUSED 分支先 `SourceVersionReader.verify_version` 实读验 SHA，再记 successful journal。失败由统一异常路径写 failed attempt。
6. 没有新增许可文件、人工签收、按公司分支、第二身份库或可变的消费者存储路径接口。

## 测试环境和原样恢复

每次使用唯一新建的短 scratch `company-wiki/.tmp/w06scope-<uuid>`；ROOT 明确允许该路径以免深 evidence 路径触发 Windows 路径限制。测试结束后删除本次自有目录；既有 `.tmp` 父目录和其他任务文件保持原状。三次执行均记录 `scratch_restored=true`、`freeze_unchanged=true`。

首轮 `probes.stdout.txt` 的 13 个失败都是**审查夹具初始化错误**：fixture 未实现旧 `DownloadAdapter.discover/fetch` 协议，且 `adapter_version="1"` 非 semver。保留首轮日志和 SHA；补齐 fixture 协议及 `1.0.0` 后运行同一组业务断言通过。该首轮没有形成产品业务反例，不能用于给产品定级。独立 `pytest.ini` 仅隔离测试选项，不写穿仓库配置。

## 下一步 / STOP

ROOT 负责原 41 CLI 矩阵一次集中回放、其他非作者对 FF CaseSpec 的审查、最终并线和 PWF 汇总。本 reviewer 未重复 191 工程测试、41 CLI 矩阵、真实 OCR/数据/provider/LLM；也没有独审自己先前编写的 FF oracle。当前来源层审查证据冻结后 **STOP**。
