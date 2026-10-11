# source_root_portability — 虚拟存储根迁移回归工具（W06-CWP-PORTABILITY）

独立、离线的多根迁移与引用回放套件，检验"公司/Dayu/Dropbox 路径属于存储细节、
上层只用一个来源湖"的抽象。工具只消费本仓真实 `SourceCatalog` / `SourceVersionReader` /
版本化 export / 正常 CLI；**不修改 src/、不扫生产根、不访问真实 Dayu/Dropbox 服务或目录**。

## 用法

```powershell
python -B tools/source_root_portability/run.py --owned-root <fresh-root> --out-root <new-attempt-root>
```

- `--owned-root`：本线 owned 临时根。必须初始 absent，或只有会保留的 sentinel 文件；
  runner 只清理自己生成的 `cfg/ lake_A/ lake_B/ catalog/ logs/ scratch/` 并恢复基线。
- `--out-root`：每次运行新建 `attempt-NNNN/`（永不覆写既有 attempt），内含小报告 `report.json`
  （schema `cwp-root-portability/1`，≤8MiB，不留全 catalog/大 PDF/parsed dump）。
- 运行前必须把 PYTHONPATH 绑到本树 `src/`（runner 会校验 `company_wiki.__file__` 落在
  本树并记录各模块 SHA，防止 editable fallback 跑到别的 checkout）。

退出码：`0` 全部 PASS；`3` 产品差距按 PARTIAL/UNKNOWN 如实报告；`1` oracle FAIL
（记录虚假 PASS/契约破坏）；`2` 记录非法或运行环境不合法。

## 七个场景（固定期望由 oracle 持有，报告不得改写）

| 场景 | 检验 |
|------|------|
| S1 | 3 根（目录名含空格/中文）× PDF/HTML/原语言TXT：register→query_ref→open_version→export，精确原文 SHA 与期次/文档类保持 |
| S2 | 同 root_id/relative_path 整根 A→B + 真实临时配置重映射：旧 SourceRef 读同 bytes；policy SHA 变化必须实测观察、不作授权门 |
| S3 | 改 relative_path/跨根 = 正常重新登记：记录旧/新 document_id、source_id、contentSHA、revision 关系；identity 稳定性只对承诺字段 |
| S4 | 两根同 bytes 同 metadata 不同 priority：1 逻辑来源/2 物理副本分记；删一个 synthetic 副本后真实 reader 仍可读另一副本 |
| S5 | raw 暂不可用不伪称已验真；恢复即读回；同长度篡改→真实 SHA 拒绝；新内容=新版本，旧 ref 拒发 |
| S6 | as-of/period/document_kind 不因移根变化；非周期 IR/prospectus 不获假 FY |
| S7 | export + 无路径消费者在新短生命周期进程复现（新 PID reopen，非旧 buffer） |

fixture 只用 ≤6 个 synthetic 原件（显式 `[SYNTHETIC]` 元数据、固定日期）；
`local_company / external_dayu / external_dropbox` 仅为三个存储位置的模拟 ID。
非周期原件的 sidecar 用显式 `nonperiodic` 标记满足 sidecar_filing_v1 完整性契约
（WU-701 N-02），describe 层不产生假 fiscal_year。

## 组件

- `fixture_builder.py` — synthetic 湖 + 真实 YAML 临时配置（含含空格/中文根目录）。
- `scenarios.py` — 7 场景实现；`CountingReader` 统计 source-read 调用；
  读取一律经真实 `open_version(ref, purpose="source_export")` 字节验真。
- `consumer_spy.py` — 跨进程无路径消费者探针；`sys.addaudithook` 记录一切文件访问
  并按栈归属（company_wiki / harness / consumer），raw 直开即违规证据。
- `oracle.py` — 运行记录判定器（schema `cwp-root-portability/1`）：持有固定期望，
  拒绝已知虚假 PASS 形态（漏 reopen、SHA 只核 metadata/假 receipt、消费者偷开 rawPath、
  移根造假日期、物理副本冒充逻辑来源、无 policy 观察、清理越界/丢 sentinel、
  改写 expected、UNKNOWN 混入 same-ID 通过）。畸形记录=INVALID_RECORD，不算产品缺陷。
- `report.py` — attempt 目录、代码身份（HEAD/模块 SHA/绑定）、小报告写出。
- `run.py` — 编排、基线/sentinel 清理、oracle 复核、退出码。

## 测试

```powershell
python -B -m pytest -q tests/unit/test_w06_root_portability_oracle.py tests/integration/test_w06_root_portability.py
```

- 单元：oracle 反例（RED→GREEN 过程见 docs/handoffs/w06-cwp-portability/logs/）。
- 集成：真实 SourceVersionReader + 临时 catalog，不 mock 字节；跨进程 spy 只放行
  正式 reader 的存储操作；sentinel 清理边界。
- 手动大节点：完整 runner（默认 CI 不自动遍历真实湖；跨仓/多根完整回放保留手动入口）。

## ROOT 工具层修复后接口（替代以上旧 fresh-root/命名目录清理说明）

--owned-root 为临时容器，可已存在。每次新建唯一 w06-owned-* child，所有 synthetic
湖/config/catalog/HOME/TEMP 都在该 child 中；只删本次创建项。既有 cfg/lake_A/lake_B/
catalog/logs/scratch、文件和空目录保留；初始化失败也恢复。不扫描/备份用户资料湖。
--out-root 按 attempt 追加证据，不覆盖既有文件。两容器互不包含，写前拒绝
existing reparse/symlink 祖先。child只继承平台启动变量、synthetic HOME/TEMP、
禁dotenv；生产模块导入前装离线/凭证文件audit guard，不继承API keys。

CLI stdout/exit/stderr/bundle/manifests原样保留，不能由Reader facts替换。消费者直接
open完整输入SourceRef，错size/MIME/schema真实拒绝。Oracle要求S1-S7完整、实际wire、
所有原件返回bytes/最终恢复、固定期次与实际根映射；verify_version不冒充bytes。
畸形嵌套JSON返回INVALID_RECORD，诚实PARTIAL/UNKNOWN不補PASS。

四doc_key共三distinct逻辑来源。S2/S6遍历四个ref别名；TXT-copy共享ref，不能声称
四个不同physical路径因此被读取。S4真删除synthetic主副本后的读取才证明备用physical。
CountingReader统计Reader API调用（含query/describe/预期失败），不是成功bytes次数。
runtime.py负责创建归属、最小env、离线child bootstrap。

范围仅Windows本地synthetic Reader/catalog/CLI；不代表真实云、Dayu/Dropbox、OCR、
LLM、投资质量或POSIX验收。本卡只在大节点跑短套件+完整synthetic runner。
