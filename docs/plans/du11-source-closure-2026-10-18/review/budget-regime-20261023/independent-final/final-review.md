# 预算制度独立终审：PASS（仅本节点）

## 结论

ROOT 首版被独立真实内存 PDF 找到的两个问题均已从共享 owner 修复；原断言未放宽。最终版本通过 **99 项**预算/真实源端口/inventory 回归，以及 **47 项**真实 PDF 正式摘要、公开读取、同 run 重启和 generation/partial 兼容回归。探针导入格式整理后，原 4 个独立断言再跑全绿。具体时间、源码 SHA 和清理在 `final-review.json`。

## 已确认的行为

- 当前母额度来自单一配置：10M tokens / $20；历史 charges、FX hold 和 unknown 不重置。公司 150K tokens / $1 是软目标，超过不产生第二硬门。
- 同一内存 PDF 经真实生产 parser 和 selector，始终是同一账号。0 / 1000 / 20,000 / 16M 的配置均真实生效；parser 已用计量不在 selector 重置。
- 20,000 工量时仍保留原有 3 个可用来源片段，状态 partial；计算耗尽诊断现在如实给出 `used=19913, limit=20000, requested=null`。原拒绝大小未保留就不猜。
- 此 partial 的依赖现在是 partial；提高工量后真实 compare 为 unavailable，生产缓存判断 false。16M 同源能读得 4 个片段；只改母费用不改变来源语义 identity，只改计算工量会改变 current trace。
- 同 run 的冻结 generation 继续可用；合法 partial 不因缓存不能跨 run 命中而丧失正式摘要能力。真实 PDF loopback 摘要及公开导出、同 run 重启通过，未增加人工审批或新签收门。

## 独立性与收据

生产作者是 ROOT，本审查未改生产源码、正式测试、配置或 Git。真实探针只在自己的报告目录写临时 policy，PDF 仅存在内存；未读真实公司 PDF、密钥或付费服务。HTTP 只使用测试自有 loopback。

首轮 `2F71P` 保留在 `independent-initial.txt/xml`、`initial-review.json` 和 `production-probes-initial.json`。冻结初始探针原字节归档为 `probe_budget_production_initial.py.txt`，不是可执行测试或替代实现。最终 `independent-final.txt/xml` 为 99P/7.22s，`cache-boundary-final.txt/xml` 为 47P/36.73s，`probe-final.txt/xml` 为 4P/5.98s。前一版本 HTTP/生产端口 13P/10.06s 独立留存。

47 项测试后 hook 一度记录自动清理 false，仅残留本轮三个 SQLite 夹具目录。已检查最终绝对路径严格属于本次 effective pytest 根，进程结束后只删除这一个新建根并核实恢复不存在；没有清理历史根或原件。全部五次本审查 pytest effective 根、临时 policy 及报告内 `__pycache__` 已确认不存在。

## 范围限制

这是预算制度工程节点的独立通过，不代表 W08 来源语义、真实公司摘要/RF 矩阵、外包 W09/W11、审查技能低预算逻辑或全部 PWF 已完成。最初将 package 误当 .py 路径的读错已明确撤回，未列为产品缺陷。

## 普通回归的固化检查

ROOT 将两个反例固化到 `tests/unit/du11_production/test_document_work_policy.py`。本审查逐行只读确认：仅写 tmp_path policy；env/socket 用 monkeypatch 自动恢复；PDF 内存生成且文档上下文关闭；未替换真正 parser/selector，只有观察子类；partial 阈值按当前实际全量工量比例取得，不绑定公司、固定20,000或历史效率。无测试污染。ROOT 报告该永久组2P/4.11s，本审查未额外重跑可选套件。该最小 manifest 只检验缓存 predicate，完整同run生命周期由前述独立47项实际验证。
