# FF 与 CWP 有限下载的离线组合验收

2026-11-16，ROOT。FF 公开 CLI 使用 `dd7162172718e8276a809e9c205e3c80da06141a`，本机和远端 main 一致。CWP 在 `ac7b54d8900952f4df669896836d06b2694a54a9` 上补测试，其生产代码承接已发布的 `12e65fe7d6f954ef93bed16a257e5821eb02e5c8`。本轮仅改 CWP 测试和 PWF。

## 复现与修复

1. 按历史 FF 1.1 入口提交相同期次和下载意图。缺 `acquisition_limits` 时，FF 已调用 CWP 的 `ensure`，CWP 在启动 provider 前拒绝。FF 的下载计数为零。补齐字节、时间、费用三项后，原入口可完成采集，故修复正式 T3 请求无需迁移协议版本。
2. 已有 CWP 正向回归返回 `adapter candidate security_id does not match request`。两组夹具的 provider 候选没有回显证券 ID。修复合成候选，另留缺证券 ID 的反例，确认候选仍被拒绝且不会启动 fetch。
3. 补齐身份后，原回归的 2 秒整体测试限时仍会在发现阶段用尽，计划验证的 fetch 错误路径没有运行。将合成测试的操作限时设为 15 秒，保留 adapter 的 5 秒单次超时和模拟挂起路径。实际生产请求的契约和预算未变化。

## 走过的路径

| 验证 | 结果 |
|---|---|
| CWP 公开 acquisition CLI | 11 项通过，覆盖有界成功、零重复下载、身份缺失、超时、失败清理与恢复 |
| CWP acquisition 用量 | 10 项通过，包含隔离 loopback 传输和操作累计观察 |
| FF → CWP | CN、HK、US 各一项。FF 1.1 补齐限额后首次 `capture_ready` 且只下载一次，重复请求保持同一来源、原文 SHA 及 mtime；FF 2.0 `reuse_only` 返回无需物理路径的 SourceRef，CWP 公开 reader 按引用重开原件并核对精确字节 |
| 防误复用 | 在 CN 夹具变造一字节，核对有无下载意图均无新 provider 调用、无覆盖，精确读取不输出未经验证的字节 |

组合首次共 **24 passed / 113.99 秒**。独审指出测试项目内的临时资源应主动清理，随后加入子目录自动清理和起止空目录断言，并断言缺限额请求已到达 `ensure`。最终三项 FF 组合 **3 passed / 41.22 秒**，与第一次 24 项运行分别记录。两次 pytest 临时根清理收据均为 `removed=true`。Ruff 和最终独立审查通过，覆盖测试隔离、合同完整性与验收表述。

在仓根使用本机已审查的 FF checkout 复验。先核对其 Git 版本，另可只跑最后一个测试文件快速复验三市场。没有设置 `CWP_TEST_FF_ENTRYPOINT` 时，新的 FF 组合会跳过。

```powershell
$env:CWP_TEST_FF_ENTRYPOINT = '<filing-fetch 仓库的绝对路径>/scripts/fetch_filing.py'
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -m pytest -q -p no:cacheprovider tests/integration/test_acquisition_failure_cli_e2e.py tests/integration/test_m3_acquisition_usage_cwp.py tests/integration/test_ff_bounded_acquisition_e2e.py
```

| 独审绑定文件 | 审查时工作树字节 SHA-256 |
|---|---|
| `tests/integration/test_ff_bounded_acquisition_e2e.py` | `a9c0f1ce23fdb2bea47d3a835b76c5e3b7c558657321a606cc583c27aeb6549e` |
| `tests/integration/test_acquisition_failure_cli_e2e.py` | `926ac952c0b740c83045728077f769171255bcf60de220c2e1471205569afc04` |
| `tests/integration/test_m3_acquisition_usage_cwp.py` | `07643077cbd2342e6630b68d5be8b06d28907efd064f4742f863775507e6b7d0` |
| `tests/support/acquisition_cli_fixture.py` | `6a85f264b44034869ffedbdc6c0ffd28806b6735799415726a8f50a42b98aa4d` |

## 剩余 owner 交接

此次用宿主 Python 3.13.9、真实 FF 和 CWP 公开 CLI、模拟 provider 与独立临时目录。未访问外网 provider、调用收费 API 或写入生产库。CWP 组合覆盖 FF 1.1 下载及 2.0 复用与读取；FF 自有 T3 的真实下载验收与 RF assurance 仍单独收口。

- **FF**。截至 21:57 UTC，`dd716217` 的四个正式 T3 下载请求仍待补 `acquisition_limits`，重复调用辅助函数也走该合同。FF owner 在本仓以当前主线复跑 T3，记录实际 Git 版本、结果和隔离清理。
- **RF**。截至同一观察，本地 `be0caa4b506a4174d1bad860946ade73279627d4`、远端 `f2215959d33abc76778342a95d39a8e38191da75` 相差九提交。仍有三份跟踪 assurance 文件变更。周跑 `20261115T084227Z / not-ok` 绑定原 FF `1dfd818`、RF `f2215959`、CWP `0e741063`，由 RF owner 对齐当前 PWF 和版本。
