# RF Linux 修复增量独立复审

第三版通过独立复验。SQLite 不可用时，同时首次创建显式 outbox 的两个写入者都能保留原始观察。原包冷查、链接和特殊节点防护通过复验。

## 第三版发布候选复验

- 基线 Git 对象和检查时的本地远端跟踪引用均为 `adea01132d71a3caa73777fb241b201334ead773`。第三版补丁 SHA-256 为 `6de8003741375610603adf2039bc9e3e270360bd5d9d9e46727220811f5bc1b9`。
- 对 `scripts/owner_atomic_io.py`、`scripts/rf_feedback_outbox.py`、`scripts/rf_job_feedback.py`、`tests/test_rf_job_feedback_roots.py` 的基线 Git blob 与候选文件重算所有八个 SHA-256，完全吻合第三版冻结清单。相比第二版，只有 RF 文件打开逻辑和回归夹具变化。
- Windows 与 WSL 各三次执行下文同一独立并发探针。SQLite 可用及状态目录受阻的两种情况下，每轮均记录两条、匹配两条、冷查证明两条。恢复后 `flush` 的 `found=0/remaining=0`，出箱仍只有原来的两条。
- 独立执行冻结版 `tests/test_rf_job_feedback_roots.py`。WSL 18 项通过，10.29 秒。Windows 14 项通过、4 个 POSIX 专用用例跳过，25.45 秒。覆盖真实 owner 观察，现代错误运行号和尝试号，旧 canonical 路径，旧原包缺失、错号和已确认原包，描述符替换，以及排他创建竞争中出现的链接和 FIFO。WSL 原探针另外验证父目录别名、两个出箱形态的链接与 FIFO、原 pending 恢复后投递一次。

首次排他创建遇到 `FileExistsError` 时，第三版按共同文件接口重新确认实际叶子，再用已有文件标志打开一次。路径、文件类型和描述符身份核验仍先于读写，投递主体和原包归属规则保持原语义。独立探针在各自临时目录运行，仅使用合成观察。候选、发布检出及实际作业数据均为只读。

### 发布测试夹具补正

补正后的 `tests/test_rf_job_feedback_roots.py` SHA-256 为 `3684b8ea51d2ae5a88422f09552e70387929d61bd7145694f9f00adf103c9109`。与上述冻结版相比，唯一变化是把符号链接和 FIFO 建到同目录的临时叶名。排他打开回调仍在首次系统打开前将竞争节点原子移动到目标名，原有平台标记和断言均保留。重新计算发布候选的三个生产文件 SHA-256，均与已验第三版一致。

在自清理 WSL 临时目录复制精确测试文件，分别复跑 `test_rejected_leaf_won_the_first_creation_race[symlink]` 和 `[fifo]`，2 项通过，2.77 秒。补正通过独立复验。

## 第二版独立复验

本轮仍以 `adea01132d71a3caa73777fb241b201334ead773` 为基线。补丁 SHA-256 为 `6e347ddb1024f5632ff11909d35292a7b35027b2e4152530ef033af8032e6ff8`。对 `scripts/owner_atomic_io.py`、`scripts/rf_feedback_outbox.py`、`scripts/rf_job_feedback.py`、`tests/test_rf_job_feedback_roots.py` 的基线与候选重算全部八个 SHA-256，均与第二版清单吻合。

| 实际复验 | 结果 |
| --- | --- |
| 冻结源码的 `test_rf_job_feedback_roots.py` | WSL Ubuntu Python 3.12 为 15 通过，11.37 秒。Windows CPython 3.13.9 为 13 通过、2 个 POSIX 专用用例跳过，25.78 秒。 |
| 真符号链接和 FIFO 探针 | RF 配置的父目录别名可用。原包运行环境中重新挂到被移出的相同字节，目录叶及显式单文件叶均拒绝。两类真实 FIFO 均及时返回。 |
| 已有状态下的单文件恢复 | 单文件被链接替换时保留原 pending，未写入链接目标。恢复为普通文件后投递原记录一次，再次发布无重复，原包可冷查。 |
| 正常状态库下首次并发写入 | Windows、WSL 两条独立观察均写入并可验真，无待补投。 |
| 状态不可用时首次并发写入 | Windows、WSL 各只保留两条中的一条。取消状态路径上的故障后，`flush` 返回 `found=0/remaining=0`，丢失记录仍无法冷查。 |

### 需要修复的直投竞争

隔离探针 `.planning/r25/rf-r2-independent-probes.py` 使用真实 `publish` 和 `flush`。以普通临时文件占用 SQLite 状态根，让两个线程进入已有的显式单文件直投分支。用两方 barrier 控制两次首次 `os.open(... O_CREAT | O_EXCL ...)` 的时序，实际创建、文件追加和日志读取仍走操作系统。两套操作系统均得到 `recorded=1`、`matched=1`、`read_proofs=1`、`after_replay=1`。正常 SQLite 对照为 2、2、2、2。探针仅使用合成观察和独立临时目录。

第二版正确使用排他创建保护已存在的文件。竞争失败的 `FileExistsError` 从 `open_regular_file` 到达直投错误处理，当前观察已无 SQLite 可以暂存，因此不再可恢复。应在这一预期竞争后使用同一普通叶及描述符验证重新打开获胜文件，再在原投递路径追加。拒绝链接、特殊文件及不可访问普通文件的处理继续由文件接口负责。

## 第一版历史记录

### 冻结范围

- 本地 `origin/main` 的观察基线为 `adea01132d71a3caa73777fb241b201334ead773`。本次结论绑定其上的三文件候选增量。
- 补丁 SHA-256 为 `3986ab0d22cc27de8e4a3072e58b2f3c9767d4fbf2429e1cc1e2297ae91ec298`。
- 已分别从候选目录和基线 Git 对象重算 `scripts/rf_feedback_outbox.py`、`scripts/rf_job_feedback.py`、`tests/test_rf_job_feedback_roots.py` 的 SHA-256，六个值均与冻结清单一致。

### 已验证行为

| 项目 | 独立结果 |
| --- | --- |
| 实际 owner 观察 | 夹具使用真实 RF `JobFacade.submit` 产生的 `job-usage` 观察，冷查以保存的运行和尝试号关联。 |
| 现代身份 | 单独替换运行号或尝试号，返回 `unknown/native_attempt_mismatch`。 |
| 历史记录 | 可证的 canonical 作业与阶段组合可以冷查。缺外层关联号的旧包装器在原生 outbox 保有相同原包时可以冷查，覆盖目录的 ready 标记已经被消费和旧单文件两种形式。错号或缺原包返回 `unknown/native_attempt_mismatch`。 |
| 副作用 | 正负对照通过 RF 公开冷查入口，比较测试状态树的内容。目录普通包缺失及注入 `PermissionError` 均返回未证。 |
| 回归 | Windows CPython 3.13.9 执行 `test_rf_job_feedback_roots.py` 的 11 项全部通过，耗时 24.44 秒。作者的留存 Linux 定向记录为 34 通过、3 个平台专用项跳过。 |

### 已修复的第一版缺口

`scripts/rf_feedback_outbox.py` 的 `was_published` 在目录分支直接打开计算所得的包名。独立 WSL Ubuntu 探针在私有临时目录用实际 RF `publish` 创建一条合成 `job-usage` 记录，再把原包移到 outbox 外的同一临时目录，并在原包名放置指向移出文件的符号链接。结果依次为 `regular_packet=true`、`missing_packet=false`、`redirected_packet=true`。探针只有合成字段，退出时自动清理。

```python
with tempfile.TemporaryDirectory(prefix="rf-self-audit-") as work:
    root = Path(work)
    os.environ["XDG_STATE_HOME"] = str(root / "state")
    os.environ.pop("RESEARCH_FEEDBACK_OUT", None)
    os.environ["RESEARCH_FEEDBACK_DIR"] = str(root / "outbox")
    row = {
        "owner": "revenue-forecast",
        "run_id": "synthetic-rf",
        "attempt_id": "synthetic-attempt",
        "step_id": "job-usage",
    }
    publish(row)
    packet = next((root / "outbox").glob("feedback-*.jsonl"))
    assert was_published(row)
    detached = packet.rename(root / "detached.jsonl")
    assert not was_published(row)
    packet.symlink_to(detached)
    assert not was_published(row)  # Frozen candidate returns True here.
```

目录分支需要对预期包路径的普通文件身份做实读确认。单文件分支也直接 `Path.open`，适合共用读取原包的逻辑。应保留显式配置根的合法目录别名与权限不足时的 `unknown`，并避免 FIFO 或特殊文件阻塞冷查。补相同契约的回归后再冻结。
