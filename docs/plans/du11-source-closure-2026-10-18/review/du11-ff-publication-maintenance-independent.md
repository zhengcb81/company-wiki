# FF 发布维护 delta：独立审查 PASS

受审 HEAD：`a9c2dcf7de2e70f50cb18caa8b4b038464391f9d`，工区为 ROOT 的 `du11-ff-reception/filing-fetch`。只审四个工具/测试文件；没有修改源码、作者树、生产配置、原件或安装副本，没有提交/推送。

## 根因与范围核验

复杂度 CLI 以 GBK 写出包含中文的原始 JSON，而调用者按 UTF-8 解码，会在读有效诊断结果之前失败。`ensure_ascii=True` 只改变 JSON 字符转义，解码后的路径、评分、diagnostic 字段和失败退出语义不变。未提高阈值、隐藏错误或把诊断变成许可门。

集中 CI 表由 35 到 38，恰好新增 DU11 selection、contract 和 current-reader 三个纯回归模块；没有删除旧项，没有重复项，没有加入耗时的 frozen-CWP E2E。共用 CI/push 入口保持不变。

## 版本绑定

- `tools/complexity_diagnostics.py`: `a6a0ef5e211dac9abc3874c95bb07fac23b54d8307d19c9ce6cf07fdf598ba2e`
- `tools/ci_tests.py`: `8ae5f51e611e8017439cf9748edff4e6fb17c111a33764c011e98d4b02850d96`
- `tests/test_complexity_diagnostics.py`: `603ff0d0bf772fe8293c81a9bc8f4b96558f9a01c3062aaa9d569fb7e42d8019`
- `tests/test_ci_tests.py`: `7bb9cca8c23a2e1dd35d50f3f8e56386902f6ab6ddbd1f38c8097414216f684d`
- 原 transport 继续冻结为 `4bb18006bb608c3dc706a6ca3f70e77fe03513798ff815b464aad208a8f33026`。

四文件与 transport 的执行前、实际快照、执行后 SHA 完全相同。Gold 的 135 PASS / Ruff 收据及 XML 已实际核对，绑定同版源码，未重复跑 135 项。

## 独立有限实跑

**7 PASS，0 FAIL，0 SKIP；pytest 1.848 秒，含归档准备 3.28 秒。**

- 三个新增行为：中文路径的有效/缺失输入实际 GBK 子进程输出；CI 表完整性。
- 实际 failing-pytest 子进程：非零退出与指定失败节点输出保留，scratch 恢复。
- timeout 清理反控。
- 两个额外实际 CLI 控制：路径含 GBK 不可表示的 emoji，分别正常 Python 与 SyntaxError；输出为 ASCII 字节，UTF-8 解码再 JSON 解析后路径精确不变，成功为 exit0、语法错误为 exit1，原文件字节与 mtime 未变。

运行从精确 Git 归档的自有源码快照开始，覆盖冻结四文件；只用合成输入和最小系统环境，不继承凭证或加载 dotenv，禁插件与 cache，专用 basetemp，子进程网络审计拒绝。网络尝试 0，Temp 已删除，sentinel 未变，产品源未变。

没有新增必须修复问题。可以进入 ROOT 的正常提交和推送；并不据此签收全部 CI、跨仓实际供应商、摘要内容 C 或剩余 PWF。这里验证 ASCII-compatible 的 UTF-8/GBK 流，不对任意 UTF-16 stdout 作保证。

精确命令、XML、完整前后 SHA 和清理记录见同名 JSON、`du11-ff-publication-independent-run.json` 及对应 log/XML。
