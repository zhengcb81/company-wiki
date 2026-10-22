# FF 最终整合与定点安装

状态：**COMPLETE_FF_MAIN_PUSH_AND_SELECTIVE_INSTALL**。完成本轮 FF 收尾；不代表 W03/live/整体 PWF 完成。ROOT 负责 RF 和共享总 PWF。本报告时间：2026-10-21T23:10:53.115236+00:00。

## 主线与远端

- 基线 `e8740748` → 已独审产品 `cf15aeaa` / 完整交接 `df9a1d3`，快进主线。
- 在既有 `tools/ci_tests.py:CI_TESTS` 只增加新回归文件一行，正常提交 `a1cb84da5e055e41a21305147d1991b839f47aba`。没有新工作流或门禁。
- 正常 `git push origin main` 成功，远端 `ls-remote` 精确匹配上述 HEAD。没有 force、跳 hooks 或跳测试。
- tracked clean；两个原未跟踪路径仍在：`.planning/du11-empty-placeholder-original.py`、`config/FMP_API_KEY.txt`。仅比对元数据，均未变；密钥内容未读、未提交。

## 验收

- W02 独审同最终产品 **35 PASS / 0 FAIL / 0 SKIP，9.62s**。正式报告见 `r1-w02-boundary-review-20261021.md/json`，精确 SHA 在机器收据中。
- 新回归与原 CI runner 控制：**36 PASS，9.42s**。
- 本次正常 pre-push：**899 PASS / 7 既有 SKIP / 78 子测试 PASS，132.39s**。ruff、compile、import、公共 mypy、host guard、三仓 doctor、plan verifier 和 BOM 检查全部通过。
- 7 个 skip：1 个 CWP 实际联调须显式 checkout；3 个 ET 实际联调须显式工具路径；2 个生产身份快照未提供；1 个宿主不支持 symlink。独审真实离线 CWP→FF→RF 链已另有同版留证，未将其伪装成每日 CI 必跑。
- GitHub quality：[本次运行](https://github.com/zhengcb81/filing-fetch/actions/runs/39691450316)；截至最后观察为 **in_progress / None**，不冒称远端绿。

## 定点安装

使用原 `tools/sync_installs_b3.py --plan/--install/--check`，仅交接列出的6个运行文件（包括新依赖 `ff_source_failure.py`）。3个逻辑目录解析为2个物理目标，自动去重，共12个实际文件写入；全部旧 SHA 与冻结交接匹配，当前源码规范化 LF SHA 与已审产品匹配。

安装后 selected check=0、全部 owned runtime 字节完整、outside scope drift=0。三个逻辑目录逐份 fresh-process import 与公共 `--help`，合计6次全部 exit0；断言模块来自对应安装目录。两物理目标范围外41个现有文件的名称/大小/mtime完全未变；不读取这些配置或未知文件的内容。

## 如实记录的验收脚本错误

第一轮验收脚本错误地给直接脚本 `--help` 加了 Python `-I`，Python 因而不包含脚本目录，不能导入相邻模块；报告器随后用GBK打印替换字符又报编码错。这是验收命令错误，未改产品适配它。改成显式 UTF-8、`-E` 直接公共脚本调用，隔离 import 仍使用显式目录的 `-I`；完整6次重跑全部通过，初错日志保留。最初沙箱 git status 的工区识别错误也通过既有授权的正常主机读取澄清，没有改 Git 配置。

## 保留、清理与暂停

源文档0变更、0删除；0资料下载、0模型调用、0收费/预算账本改写。未动 Dayu、IQS、RF 安装、生产配置或其他工区。网络只有本次已授权 Git 推送/验证和公开 GitHub 状态读取。

只删除本lane4个精确、验证过绝对边界的测试/cache目录，恢复初始不存在：372个文件、13,066,360 bytes；保留小日志/XML/机器收据，未测峰值。证据在 `.planning/r1-ff-integration-20261022`，各文件 SHA、所有命令与 exit 见同名 JSON。

**下一步：ROOT 将这两份收据纳入共享 PWF 提交并记录远端 CI 实际状态，然后暂停。W03 unknown-publication 叙述口和付费/真实 W07 均未启动。**
