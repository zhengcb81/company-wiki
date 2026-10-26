# C3 PDF runtime v2 独立审查

结论：**PASS，0 OPEN**。审查绑定下表当前文件；与作者 handoff 的字节/LF SHA 一致。此结论仅覆盖环境身份与运行协议，不代表真实 PDF 内容召回已经验收。

## 本次独立证据

- 作者范围内 18 项测试与审查新增 7 项反例合计 **25 passed，2.11 秒**；`focused.log`、`focused.xml` 可复核。仅有关闭第三方插件后 `asyncio_mode` 未知配置提示，不影响本组同步测试。
- 新增反例覆盖：根/声明顺序、已选择节点再次遇到冲突版本约束、多个 extras 与循环固定点、非激活/激活直接 URL、规范名称与元数据冒名、独立重算 payload SHA、禁止全环境枚举。
- 独立真实解释器 `C:/Miniconda/python.exe` 直接运行 `_paragraph_worker.py --describe-environment --runtime-config ...`；单个 src 与重复 src + ROOT + scripts 两种 PYTHONPATH 的完整 JSON 相同，闭包 **104** 个包，SHA `c84a984ccb3a56dffbfd0d4538f14ce4a27de44dec4981527a2b0c4a545cdf44`。
- 独立新进程阻止 `packaging`、`docling`、`torch` 导入，仍可导入基础编排模块并执行 v1 算法；v1 SHA 等于独立构造的旧库存算法。
- 新旧运行配置仅改变 `schema_version`、`environment_algorithm`、`environment_sha256`。旧配置 SHA 保持 `d84387132edda4dab3cc43d62a7cd9a93634914977b8da89b42ddb90f3c27a1a`；新配置 SHA 为 `077654bd7eeb016d57667ec3560e602f4de480a74c2cbb236fc1100dda942fd6`。120 秒、3 页、4 GiB 等资源限制未增加。

## 代码审查判断

v2 以所选 distribution 元数据为解析依据，根取配置运行时加 Docling。PEP508 marker 与当前节点 extras 决定激活边；晚到 extras 会重新处理节点并到达固定点。每条进入约束都验证，即使目标节点早已解析。激活的传递依赖版本/声明改变会换指纹，无关包和未激活 extras 不会污染闭包。

配置、recipe、worker 请求和响应均明确区分 v1/v2。v2 recipe 绑定环境实现代码，worker/orchestration/alignment 与模型/config/限额的既有绑定继续存在；响应中的算法、环境 SHA 与其他身份字段在接受前比较。旧 v1 没有被重新标注为 v2。可选 packaging 导入留在 v2 元数据解析函数内部。

## 最终版本

| 文件 | SHA-256（原始字节） |
|---|---|
| `src/company_wiki/source_catalog/narrative_pdf_enhancement.py` | `a54918b3a974d1460f3283a73cc87acdc3892765eee79ce7c5ebf4ee00931b60` |
| `src/company_wiki/source_catalog/_paragraph_worker.py` | `a41a1b36b45c71433e0ab8a87b62f56a8af0fd247c32ad5815484f7ec223bc65` |
| `src/company_wiki/source_catalog/narrative_pdf_environment.py` | `ead95695a148f2871d46036de9cde7a2f731719515afc590ae99a31d946c5f05` |
| `tests/unit/test_pdf_runtime_environment.py` | `921a589b07523c42395abfb81317dd109f9bbdda4084e1d93e4663a73881b01b` |

## 边界与清理

元数据/版本指纹不是 wheel 字节、任意原生库或所有 import shadowing 的完整证明；这是本方案已明确的边界。本次未下载、未加载模型、未转换 PDF、未调用 LLM，未写生产文件。ROOT 应继续进行一次真实内容验收，不能以本报告替代。

独立 TEMP `C:\Users\郑曾波\Projects\company-wiki\.planning\c3-20261026\pdf-env\independent\tmp` 已删除；仅保留本目录的反例代码、日志和小型元数据收据。所有本次子进程已返回终态；沙箱不允许 CIM 进程盘点，该失败没有被当作进程终态证据。详尽 SHA、范围和机器可读结果见 `review.json`。
