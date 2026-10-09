# W07 残余缺陷独立复验 — M2 接受

日期：2026-10-09。独立审查对象是修复后的精确提交：

- FF：`5101b76ceaadff5dee559f3599f7ea737d3b5bd5`，`C:/Users/郑曾波/AppData/Local/Temp/ff-fresh-transcript-launch-20261009`。
- ET：`c91f5f54bc2a24e7b5d6e648dba3f9d578f5fa52`，`C:/Users/郑曾波/AppData/Local/Temp/et-fresh-transcript-launch-20261009`。

**结论：W07 可接受为本地工程 M2，通过后可由 MAIN 集成。** 旧报告的 P1 解码后凭证泄漏及 P2 合法但受污染 usage receipt 均已在共同解码边界修复；不是只屏蔽单一 content 字段。已知正常原文、独立干净计量和启动状态继续保留。本次不代表 M3 真实 FMP 鉴权、套餐 entitlement、费用验收或真实公司研究通过。审查员没有修改两仓代码、配置、密钥或旧报告，也没有合并、推送或安装。

## 实际执行

只保留 OS 运行所需变量，设置独占合成 HOME/USERPROFILE、`PYTHONUTF8=1`、`PYTHONDONTWRITEBYTECODE=1`、`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`。没有读取生产密钥、ET config 或 dump 完整主机环境。FF 的非秘密测试路径 `W07_ET_TOOL` 指向上述 ET 精确提交，`COMPANY_WIKI_SOURCE_ROOT` 指向 CWP `src`。普通 OS 权限仅用于这些已授权的离线真实子进程；无外部 HTTP、实际 API 或收费。

亲自执行两条集中命令，而非引用实现者 receipt：

```text
# cwd = FF worktree；--basetemp 指向独占 TemporaryDirectory 下的 fixtures
python -X utf8 -m pytest tests/test_transcript_launch_contract.py tests/test_transcript_companion_transport.py tests/test_et_s0b_contract.py -q -rs --tb=short -p no:cacheprovider --basetemp <owned TEMP/fixtures>
# cwd = ET worktree；另一独占 --basetemp
python -X utf8 -m pytest tests/test_launch_capability_contract.py tests/test_transcript_api.py tests/test_provider_cost_capability.py -q -rs --tb=short -p no:cacheprovider --basetemp <owned TEMP/fixtures>
```

| 实际检查 | 结果 | 工具输出证据 |
| --- | --- | --- |
| FF 三模块集中回归 | **67 passed，0 skipped，6.93s** | chunk `b2471c`，exit 0 |
| ET 三模块集中回归 | **73 passed，0 skipped，7.31s** | chunk `abec76`，exit 0 |
| 独立配置相对密钥文件 → 真实 ET CLI/supervisor/worker fake HTTP 桥：正常原文和转义泄漏各一例 | **两例通过**，各 fake GET 1，实际外部 GET 0 | chunk `609b1a`，exit 0 |
| 独立解码及 receipt 原反例补查 | **8 组断言通过** | 同上，exit 0 |
| 最终两仓 HEAD/status/diff check | 精确 SHA 不变，两仓 status 空，diff check exit 0 | 本次最终只读命令 |

运行原契约模块也验证了 SHA/身份/类型/期次错误拒绝、原文 JSON 字节保持与 SourceRef 重用。三个实际 ET 预检市场/交易所调用不跳过；HKEX/未知交易所/无密钥的已测 HTTP 0 保持 0，不能误称未知或已鉴权。成功 filing SourceRef 不因 companion 不支持而丢失。

## 逐项旧缺陷复验

| 旧问题 / 必要不变量 | 实际观察与结论 |
| --- | --- |
| ET v1/v2 content 的合法 `\uXXXX` ASCII 转义 | 两种输出均拒绝为 `provider_credentials_leaked`；没有 `content_utf8` 或 `provider_payload_base64`。真实 supervisor 用量保留 requests=1、实际响应字节数，runtime 子目录为空。**P1 已修复**。 |
| JSON 已解码键、字符串值、嵌套数组及重复键覆盖 | FF/ET 新合同直接覆盖全部类型；另用不同合成哨兵独立验证 nested value、object key、nested array、先污染后 clean 的重复键。pairs hook 在 dict 合并丢弃重复值之前执行检查，数组叶子也被扫描。**共同边界成立**。 |
| FF 外层 escaped error_code 与 base64 provider JSON | 两仓集中用例均拒绝；真实恶意 child 的纯字母数字 key 不进入公开 reason。base64 解码后再按 JSON 语义检查，不仅比对原始字节。**P1 已修复**。 |
| 任意 child-controlled 看似合法字母数字 reason | 未在有限 producer error 枚举中的字符串变为固定 `provider_unavailable`，不转抄该文本。已支持错误的旧合同继续通过。**已修复**。 |
| 合法 JSON 的受污染 receipt：明文/转义 detail、嵌套 metadata、重复键 | 对受污染回执，requests/response_bytes 为 null，started 为 null，complete=false；没有凭空归零。不同哨兵对 plain/escaped 两种 receipt 独立补查也成立。**P2 已修复**。 |
| stdout 泄漏与独立干净 receipt 同时发生 | 固定泄漏分类仍保留 receipt 的已测 requests=1、response_bytes=12、started=true、complete=true；真实 ET bridge 进一步保留 fake GET 1 及实际 raw 字节数。**干净计量没有被误抹掉**。 |
| 正常 configured key 与原文保真 | 独立桥让 FF 从所选 config 的 `keys/selected.key` 解析相对路径；key 只经 ET 子环境，未在 stdin/argv/公开 DTO，CWP 子环境剥离两个 FMP 变量。成功结果的 base64 原文与输入完全一致，SHA 匹配，配置和 key 夹具字节未变化。**没有 scrub/rewrite 原件**。 |

## 独立真实桥的具体形态

这条补查没有 mock FF `_run_bounded_json`，也没有替换 ET CLI、supervisor 或 worker。每例独占 TEMP，过程如下：

1. 建立 `config/company_wiki.json`（仅 `fmp_api_key_file: keys/selected.key`）、合成 key 文件、provider JSON 夹具、空 runtime 目录。
2. 一个只存在于 TEMP 的 wrapper 导入精确 ET `transcript_tool`，接收 FF 实际命令的 `--request-stdin --include-source-payload --report-usage`。wrapper 只做 safe boolean 断言：ET 获得预期合成 key、`FMP_API_KEY_FILE` 不在子环境。
3. wrapper 调用 `transcript_tool.main(..., _retrieval_launcher=tests.test_retrieval_runtime:build_fake_session, _retrieval_spec=fake_spec(...), _retrieval_temp_root=<fixture/runtime>)`。这是既有私有 fake HTTP seam，不是公开环境后门。
4. 父进程用实际 `EarningsTranscriptsTransport(..., config_path=<fixture/config/company_wiki.json>)` 调 `_et_result`，NASDAQ/FY2026/Q3/as-of 2026-09-30，timeout=10s、max_bytes=1,000,000、max_cost_usd=0.00。
5. 正常例必须 fetched、base64 原文等于输入、SHA 一致；泄漏例必须固定 leak reason 且无正文/payload。两例真实 fake GET 数都为 1、计数和字节正确、clean receipt 完整、started=true。两例配置/key 前后字节相同；runtime 均清空；外部请求数 0。

独立语义补查使用不同于实现者用例的纯字母数字合成 key，将其全部 ASCII 编成合法 Unicode JSON 转义。直接验证 `_credential_exposed` 的 escaped reason、四类 `_stream_credential_exposed` 结构，以及 plain/escaped contaminated `_provider_usage` 和一份 clean receipt。报告不保留 key 值或 hash。

## 清理与范围限制

三处本次独占 TemporaryDirectory 在终端进程结束后自动恢复为不存在：

- `C:/Users/郑曾波/AppData/Local/Temp/w07-close-ff-vkc1hg22`。
- `C:/Users/郑曾波/AppData/Local/Temp/w07-close-et-c2wa74xg`。
- `C:/Users/郑曾波/AppData/Local/Temp/w07-close-independent-hojafg4a`。

未创建 pytest cache/pyc，未更改生产 raw、source_catalog 配置、已安装技能或主线 Git。两审查 worktree 继续保留供 MAIN 集成，不删除别人的 worktree。唯一持久写入是本报告；旧暂缓验收报告和实现者历史 RED、incident 记录保持原样。

隔离 FF worktree 没有 CodeGraph 索引；没有初始化或修改索引。此次按精确已指定 source diff 和测试模块检查共同边界，不声称进行全仓结构审计。当前缺陷定位充分，停止扩大可选测试。

MAIN 后续仍需：ET 先于 FF 集成接受的完整两个提交序列；把新 FF 合同模块纳入已有 shared CI/pre-push 清单；选择性同步运行文件与既有配置 key 路径；最后在现有累计预算内做 M3 真实支持市场的 FMP 鉴权/entitlement/用量记录。W08 timeout/failure 的更广原因及累计用量传播不在本次 M2 修复范围，不能据此声称完成。
