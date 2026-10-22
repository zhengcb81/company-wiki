# W02 独立复核证据（封存）

状态：PASS_ENGINEERING_BOUNDARY_ONLY；35 PASS / 0 FAIL / 0 SKIP / 9.62s。

- FF 产品：cf15aeaa90667a8b8aeac01af713dd984f057fe5
- RF 产品：768b6dd392d98df67d8eeb1d7ce428ef014cca7c
- CWP 离线 producer 工区 HEAD：3b80e0ec9d35db7777d00f419dfe9d5072306f8a；source_catalog 冻结 0622f242。
- 非作者独立反例；0 API / 0 下载 / $0。保留初始 18P/3F 和费用矛盾 2F；最终 35P。
- source-before.json / source-after.json 绑定全部改动 runtime 文件和冻结 producer 的 Python 源码；final-receipt.json 保存本次实际命令、环境、UTC 和退出码；cleanup.json 证明 TEMP 恢复初始不存在。

## 复跑

先确认源工区在上述版本且文件 SHA 与 source-before.json 相同；本包不自动 checkout/install 或获取原件。工作目录为 company-wiki 母仓；使用其已有 .venv。下面的 TEMP 是新的独占测试根，若它原本存在应换一个，测试后只删除此次创建的根。默认本机 TEMP 不可写，所以显式设置。使用这些现有工区不会发送 API 请求。

```powershell
$env:W02_FF_CODE_ROOT='C:/Users/郑曾波/Projects/filing-fetch-r1-boundary'
$env:W02_RF_CODE_ROOT='C:/Users/郑曾波/Projects/revenue-forecast-r1-boundary'
$env:CWP_V2_CODE_ROOT='C:/Users/郑曾波/.codex/worktrees/du11-extractive-runtime/company-wiki'
$env:PYTHONPATH=($env:CWP_V2_CODE_ROOT+'/src')
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
$caseRoot='C:/Users/郑曾波/Projects/company-wiki/.planning/r1w2-review-replay'
if(Test-Path -LiteralPath $caseRoot){throw 'choose an initially absent owned test root'}
New-Item -ItemType Directory -Path $caseRoot|Out-Null
$env:TEMP=$caseRoot
$env:TMP=$caseRoot
$suite='docs/plans/du11-source-closure-2026-10-18/review/r1-w02-boundary-review-20261021/test_boundary_independent.py'
& '.venv/Scripts/python.exe' -m pytest $suite --rootdir (Split-Path $suite) --collect-only -q -p no:cacheprovider
& '.venv/Scripts/python.exe' -m pytest $suite --rootdir (Split-Path $suite) -q -p no:cacheprovider --basetemp ($caseRoot+'/pytest') --junitxml ($caseRoot+'/replay.xml')
```

实际原始命令使用 `.planning/r1-w02-independent/test_boundary_independent.py`，该文件与封存副本字节相同。复跑时报告路径应指向新的自有目录，不覆盖封存证据。必须保留失败原因，再按解析绝对路径确认属于自有根后清理测试临时材料；不要删除生产文件或其他 owner 的临时目录。此说明不启动任何定期重跑。

## 边界

真实离线 CLI 控制使用合成 HK 身份及空本地 catalog；没有用真实公司 holdout，也没有运行正式模型、安装副本、远端 CI 或新 W01 producer。完整审查结论和下一步见上一级同名 MD/JSON。按用户要求，本次封存后停止。