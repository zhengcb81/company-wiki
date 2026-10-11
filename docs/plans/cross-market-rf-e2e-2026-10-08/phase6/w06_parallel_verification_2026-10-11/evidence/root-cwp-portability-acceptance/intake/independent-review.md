# W06-CWP-PORTABILITY 独立只读验收

## 结论

**FAIL_HARNESS_ACCEPTANCE。原交付暂不直接验收并入主线。** 可由 ROOT 在隔离树接入原提交，集中修复测试工具后一次验收。当前没有证据要求改生产 `src`。

真实来源层的轻量合成端到端回放 **PASS**；阻断项是测试工具可能删旧文件、替换实际证据、把漏测/错误证据判绿，以及刷新消费者收到的引用。不能用这套工具目前的 PASS 证明虚拟存储完整正确。

## 提交与冻结核对

- 基线：`01ea86a37edb5506d6269b6e10d9cb56a1270efd`。
- 代码：`49afd8738b38f45507ccc58fa4bab27c638addf7`；交接：`562bb87971fe889dd974261ef75a1e6344469894`、最终 `f8d5e0f4f6047375fdaef38e15e54edff2abe61d`。
- 23 个已提交改动全部在卡的排他写集；没有 `src/scripts/config/旧 tests/CI` 修改。工作树只有 ROOT 固定输入 `docs/handoffs/w06-cwp-portability/input/` 未跟踪。
- 22 个 handoff 文件的字节数和 SHA 全部匹配；6 个 dispatch 输入匹配；9 个引用是**源代码文件引用**，Git blob 均匹配，不是九份真实公司原件。部分工作树物理换行与 blob 不同，按 EOL 等价记录，未误判产品改动。
- author 的 33 PASS、7 场景 PASS、7.424 秒、51 读取仅按其原留证记录，未重复全套运行。author 原 RED/FAIL/PASS 文件均未覆盖。

## 需集中修复的共因

| 级别 | 位置 | 已证实的问题 | 修复方向 |
|---|---|---|---|
| P1 | `run.py:74` | cleanup 按 `cfg/lake_A/lake_B/catalog/logs/scratch` 名字递归删目录，独立反例实际丢了 3 个已有哨兵；`raw_unchanged` 仍为 true | 每次新 attempt 工作区，按本次创建归属删除；输出与生成区分离；在写/删前处理重叠、碰撞、symlink；保留已有文件和空目录 |
| P1 | `scenarios.py:396` | 实际 CLI 返回的 manifests 被 reader facts 整体覆盖；本地读成功可能掩盖新进程/导出失败 | 保存原始子进程 JSON/退出状态，不补造 manifests；真实 child 成功及完整引用回放必须成为判据 |
| P1 | `oracle.py:46,128,325` | 7 个错/漏证据反例仍 PASS，弱类型反例整批 AttributeError | typed shape + 精确七场景与各文档覆盖；仅真实返回字节算 read；校验实际根/新版本/恢复/路径和固定期次真值；UNKNOWN 不编日期，输入错误结构化报告 |
| P1 | `consumer_spy.py:172` | 收到 wrong byte_size 引用后 query_ref 刷新，绕过完整引用 pin | 直接打开收到的完整 SourceRef；查询只能诊断，不得替换；错误 size/MIME/schema 是独立反例 |
| P2 | `scenarios.py:232` | 子进程继承整个用户 env | 最小运行 env、synthetic HOME、明确模块路径/配置；不继承 keys/真实 HOME；保持离线和 synthetic scope |

输出根位于 generated subtree 的删除风险来自同一 cleanup 静态路径；本轮没有额外调用 worker runner 破坏输出哨兵。实际删除反例只在我的新独立测试根发生，已恢复原 baseline，再将该新根恢复 absent。这里要求的是测试正确性，不是新的人工许可或身份门禁。

### 保留的独立 FAIL 向量

`probes.json` 中以下反例实际都得到不正确的 PASS：仅留 S1、移根只读一个原件、S5 新版本读取失败、把 `verify_version` receipt 冒充返回字节、错 after_roots、S7 导出有 path 字段、年度报告把 fixture 真值与观测共同改为未知 FY/period。`S2.actual=[]` 还会抛 AttributeError。工具的普通 SHA 错误反例仍能拒绝；结论是上述覆盖缺口，不是声称所有 oracle 校验失效。

## 当前主线真实回放

`reader-e2e-attempt3.json` 的实际运行主线是 `ae0ca0d3c03f4a974ff26e472860ee306959d091`；随后只读 inventory 时主线推进到 `8862372f714209cff1b218d77b5c4b8af6bc74dc`。所核 Reader/config/service/export/store/read-store 六模块与 worker 同字节，未偷用 editable 安装。

**1.843 秒 PASS**：真实 register/query/open/describe 四个合成物理原件；PDF 年度 FY2025 正确，HTML 招股与 TXT IR 不冒 FY；三 root 从 A 移 B 后旧引用仍读相同 bytes，policy SHA 真实改变；删除合成主副本后读另一个相同 bytes；同长度 HTML 篡改得到 `no_verified_location / content_sha256_mismatch`；旧 schema1 引用具名 `unsupported_version`；新进程按确切输入 ref 真重新打开并回传相同 SHA；同路径新内容获得新版本，旧 ref 具名 `no_indexed_location`，恢复原内容和登记后旧 ref 回读相同 bytes。

同一个真实主线 Reader 直接拒绝 wrong-size ref (`source_ref_changed`)，但 worker consumer 以 input256/actual255 仍返回 status ok/exit0。只调整了 spy 的观察模块前缀到真正 canonical 导入路径，没有 mock Reader 或源 bytes。

前两次独立测试环境错误均保留：第一次没有 synthetic HOME，Path.home 在初始化前失败；第二次我为长路径加入 `\\?\` 表示而 SQLite readonly URI 拒绝。第三次普通绝对路径和 synthetic HOME 正常。这两次不得算成生产缺陷或用覆盖旧 FAIL 的方式消失。

## 范围与下一步

- 我的全部写入只在本 intake；产品、共享 PWF、Git、安装副本、生产配置、真实原件均只读。
- 四个原件纯 synthetic；环境不继承 credentials，测试安装 audit hook 拒网络/凭证文件读取。网络/provider/LLM/费用均为 0；每次拥有的 scratch/HOME 最终 absent。
- 不宣称测试了真实 Dayu/Dropbox/cloud、OCR、模型信息提取、真实公司/经济质量、POSIX 或最新主线全集。本轮不增加扩测。
- ROOT 下一步只改工具层：先将以上反例固定成正式 RED，再统一实现归属清理、实际子进程证据、typed oracle、完整 SourceRef pin 和隔离 env；在一个最终节点跑短 unit/integration + 当前主线完整 synthetic runner，包含已有 owned/output sentinel、失败清理与恢复检查。不增加小节点许可，原 FAIL 留存。

详见 `intake.json`、`independent-review.json`、原 `probes.json`、三次独立 attempt 和 manifest。
