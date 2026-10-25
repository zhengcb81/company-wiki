# ST-A13 具名业务收入确认：共享语义根修

当前：108项定向测试、Ruff/mypy及独立最终复审PASS，I1–I6全闭环；已正常提交推送`26e981e1`，精确CI`40180784583`成功。不是正式摘要或当前RF验收。

## 根因与实现

具名业务确认机制和一般会计政策原先共用coverage；具体业务段在112限额下被挤掉。分号条件、逗号/whereas独立断言还需要保持真实所有者。新增source-owned business_recognition_scope用途；复用既有predicate_state断言语法，通过显式客户履约条件/同owner合同收款条件/上述业务结论保持有界状态；换主体和新句重置。原文、locator、support/context、planner和cap不改。

独审发现的归属误绑、generic假具名、缺helper缓存SHA和二次尾文扫描均先写RED，再在同一责任层修复。新helper纳入现有business_algorithms，policy版本19；没有新cache/许可/任务库。

## 证据入口

- `verification.json`：真实工具观察的RED/GREEN摘要，清楚区分全目录1606P/11环境错误与主机同11项重跑通过，不造一次全绿。
- `host-rerun.json/log`：11项主机6.29秒通过，既有自动重定位temp cleanup=true，ROOT独占根也恢复不存在。`environment-rerun`保留沙箱环境失败。
- `attempt01`：仅新topic无法跨分号绑定；未补回。
- `attempt02/03`：补回204字正文+local heading，但后续独审发现归属/缓存/扫描缺陷，因此不是最终代码证明。
- `attempt04`：第一轮修复真实回放，最终probe01仍指出合法客户控制条件缺漏和逗号/whereas串主体，不能当最终验收。
- `attempt05`：最终共享断言语法接线后的完整真实回放；原件249页、112片段/9088字、63task、work12,879,238/16M，0下载/0模型请求/0原件复制。
- `independent/initial-findings.*`与`final-probe01.json`：保留独审原发现。最终独立报告以其绑定SHA为准；旧报告不覆写。

A13具体Testing/Biology确认范围已进实际task输入；精确时段/时点金额仍未在叙述输入，因此整项仍PARTIAL。源侧10PASS/4PARTIAL/0MISSING与旧8/6/0是独立范围/时点的记录，正式模型响应和当前RF采用仍OPEN。

本目录保存必要失败和最终观察，不含原始文档副本、API响应或模型正文。回放入口`python -B replay.py NEW_ALPHANUMERIC_ATTEMPT`会原子创建新attempt，拒绝覆写旧目录，复用旧只读observer和生产compiler；既有原件/配置只读。各attempt源码SHA与source digest分别绑定，不能把最新HEAD当作历史attempt代码。

## 最终候选（attempt06）

独审I6发现新scope泄漏到0.8实际入口，已先用四个legacy真实选择器测试复现（0.8失败），再将新语义从共用description移到0.9 source projection。旧0.8完整span字典及身份恢复，0.9仍补回新段；fallback include_description=False不重扫。新语义正负例使用实际assess/project入口，不用legacy text detector冒充生产。最终108项定向9.22秒、Ruff/mypy4源码通过。独立27控制、legacy真实入口及原件/payload/旧10PASS上下文增量验收PASS；早前35项独立测试绑定前一版本，未冒充当前重跑。

最终[独立终审](independent/final-review.md)及JSON绑定6份产品/测试SHA、375源码指纹和attempt06。attempt05保留为前一候选，attempt06是最终发布候选；两者完整选中span字典与实际payload相同，按证据复用原件核真，不反复跑大检查。A13仍PARTIAL，响应NOT_REVIEWED/currentRF OPEN。

发布明细及Git LF/CRLF字节绑定见`publication.json`。历史attempt与独审报告不重签；当前节点完成，下一节点为A01/A05原生多层列表与页边家具调查。
