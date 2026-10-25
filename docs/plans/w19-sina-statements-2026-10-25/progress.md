# W19 进度

2026-10-25 ROOT建立独立Git工区、文档seed和已审研究输入，未做产品实现/生产下载/库迁移。

初始化过程：--no-checkout未建index，显式暂存清单核对在commit前拦住全仓删除；read-tree初始化后移除了此前已暂存但不属于HEAD的自有seed。ROOT据中央输入重新生成这批文档，保留工作树源码。其间两次存在性检查也在修改/提交前退出。无坏commit、无主工区或原件变化。作者继续时以真实Git记录和本计划当前入口为准。

正常pre-commit首次因用户全局cache数据库只读退出。ROOT改用本任务局部PRE_COMMIT_HOME，保留原hooks及其文件范围选择，不禁用hook、不改全局cache权限；文档seed不触发产品测试。

## 2026-10-25 作者A节点（勘察+RED+BJ）

### 勘察与夹具验证
- 双仓基线核对：CWP a3083502(基线243993d2)、FF c8b0e40(基线e0d9642)，branch codex/w19-sina-statements-20261025，tracked clean。结论冻结进findings.md（含全部接缝 file:line）。
- 18份研究夹具：`.gz`文件SHA与W19-setup.json一致(18/18)；**解压字节SHA与observations.json原始记录一致(18/18)**；解压总2,572,006B。
- 从真实夹具冻结的测试期望：BIZTOTINCO 20260630="6691287327.670000"、BASICEPS="4.330000"(ps4)、20251231 row7=BIZTOTCOST"11006675861.270000"、20231231 publish_date="20250418"(PIT反例)、fzb每期141行含5空field分组行、report_count为字符串、lrb 36期/10+10+10+6分页。

### BJ能力探针（真实有界，共2请求88B，HTTP 200）
- `bj430017 lrb type0 page1 num2` → `{"result":{"status":{"code":0},"data":null}}`，44字节，sha256=2e2fd57f...（两次抓取字节一致）。**BJ是该接口的显式capability gap**；provider对BSE必须诚实返回no_data（与sh999999同形状，不能写成覆盖PASS）。
- 证据已存 inputs/research/capture/bj430017-lrb-type0-page1-num2.json.gz 并追加observations.json记录。

### 真实RED（2026-10-25，均为缺功能而非fixture坏）
- CWP `python -m pytest tests/financial_statements/ -q`：5个collection error（`ModuleNotFoundError: company_wiki.source_catalog.financial_statements` 及 canonical_writer 缺 `ThirdPartyDatasetOriginal`）+ test_cli_subprocess 4 FAILED（子进程同样缺模块）。
- FF `python -m pytest tests/financial_statements/ -q`：collection error（`ModuleNotFoundError: ff_financial_statements`）。
- 均为被测能力不存在导致，fixture路径与SHA已先行验证有效。

### 下一步
B节点按唯一owner实施：contracts/normalize→sina_provider→schema/store迁移→writer入口→repository→service→cli→FF薄客户端+SKILL。
