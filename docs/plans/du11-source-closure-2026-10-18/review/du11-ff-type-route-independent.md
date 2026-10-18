# FF 公共 mypy 修复与 hook 路由：独立审查 PASS

范围是 ROOT FF 工区 HEAD `61011be60eb6adf18d1b272885475b053ac78267` 之后的两个小改动。已先取得实现者冻结确认，未对半成品签收。

## 精确绑定

- `scripts/transcript_reuse_selection.py`: `66600ac99f48f43fc4ca332a71edd5ce6a2671173f4a4da97f99f3f724b41269`
- `.pre-commit-config.yaml`: `85db7e3011cbd67f28c33b4208dcc52b186c75cd4f9e1aaee46265a10ff6fde7`
- transport 继续为 `4bb18006bb608c3dc706a6ca3f70e77fe03513798ff815b464aad208a8f33026`。

两文件与 transport 在原工区执行前后、独立运行的源码快照中 SHA 均相同。

## 根因修复核验

`_QUALIFICATION_FIELDS` 的值是异构 class-info（class 或 class tuple），原未注解字典被 mypy 推断成不适合作为 isinstance 第二参数的宽类型。新增准确注解是类型说明；独立 AST 对比去掉这一条注解后，整个模块与 HEAD 完全相同，六个实际 schema 值未变。没有放宽协议或拒绝条件。

既有 mypy hook 入口仍为 `python -m mypy scripts/filing_contracts.py scripts/fetch_filing.py`，`pass_filenames=false`、system language 均未变。触发路径扩为 scripts 下 Python，使新增/改动的传递依赖也触发同一个公共检查；没有新增 gate 或改成全仓 mypy。文档、测试、工具和配置路径不触发此 hook，保留文档快速路径。

## 独立有限执行

从 HEAD 精确归档构建自有源码快照，只覆盖冻结两个文件，最小系统环境、不继承凭证、不加载 dotenv/自动 pytest 插件，所有缓存与 Temp 均自有：

1. **原公共命令通过**：`python -B -m mypy scripts/filing_contracts.py scripts/fetch_filing.py` → `Success: no issues found in 2 source files`，exit0。
2. **10 项纯控制通过，0.169 秒**：六个 schema 字段错误类型仍拒绝；允许的字符串/None 日期仍保留 unknown 来源，不变成 missing；六项实际 class-info 值不变；hook 对新 helper、现有入口、嵌套新 Python 脚本触发，对 docs/test/tool/config/备份扩展名不触发。
3. 包含归档与公共 mypy 的总耗时 **4.58 秒**。Gold 已有 47 selection PASS 和 mypy/Ruff 收据已读取并绑定，未重复 47/135/102。

网络尝试 0；自有 Temp 已删除、sentinel 未变，原工区源字节不变。没有改作者树、产品源码、真实配置、原件或密钥，没有提交或推送。

无新增必须修复问题，可以由 ROOT 正常提交推送。本结论只覆盖公共导入闭包及 hook 配置触发，不声称每个无关新脚本自动进入 mypy，也不替代全套 CI、实际供应商或内容质量验收。原真实正常 push 的 mypy RED 保留，不改写历史。

精确命令、前后 SHA、归档 SHA 和清理状态见同名 JSON 及 `du11-ff-type-route-independent-run.json`，实际 stdout/pytest XML 也在同目录。
