# CWP 最终CI：三项旧oracle迁移

**已冻结，待独立交叉审查。仅改3个测试文件，未改产品代码。** 原远端41445012145及本地确切3F/1P失败证据完整保留。

## 合同与修改

1. select：正文路径文字属于原文数据。伪造大段或伪造路径正文仍按原文匹配失败`PARSER_INCOMPLETE`；真正structured metadata的`source_path`拒绝`INPUT_SCHEMA_INVALID`，effects均为空。增加C盘路径及`file://`原文的真实PDF解析/replay正控。
2. summarize：旧正文路径拒绝oracle迁移到真正`claim_id`元数据路径。单次模型调用、失败、不保存response body及零effects反控保留；两种路径正文在selected原文和最终claim中完整保留，公开`validate_against`通过。
3. source facts：累计合法80KB证据完整持久化，完整字段细节/patch、投影、重复不增写、原件不变均核对。非法JSON对象拒绝，既有错误locator/value、错误ref/原件和typed scope控制保留执行。

## 真实测试历史

- 原3node（select双参数）：**3F1P/5.51s**。
- 一次受影响短域：**22P2F/5.00s**。两F仅新增原文路径正控使用旧伪造测试span的假parser/version，真实定位replay正确拒绝；不是正文路径许可回归。
- 夹具改成实际parsed unit的`to_evidence_span`，保留真实parser/version/locator后，只复这两F：**2P/4.19s**。
- 三个改动测试文件Ruff通过。没有重复全Unit/144或产品源更改。

全部精确SHA、原始日志/XML、剩余边界与清理收据在同名JSON。后续ROOT独审、正常提交推送并跑精确CI；不能把本地短域冒作完整CI通过。
