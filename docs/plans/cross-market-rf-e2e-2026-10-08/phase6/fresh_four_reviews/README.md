# 原三家公司新执行的四路独立审查

2026-10-09。三个独立executor已封存；本节点是用户指定的完整质量审查，不是下载/派生/发布许可，不增加每步人工签收。协调员使用四个不同reviewer身份，每位只负责自己的角色，分别为每家公司输出报告；总槽位4含MAIN，所以分批调度。

## 固定输入

运行根：`C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/`。原件和本轮环境位于各scope声明的独占根，保留到四审完成再由MAIN按所有权恢复；不克隆整库，不重下载或新收费模型调用以补审。

| run_id | manifest SHA-256 | 文件引用 | 执行/证据包 |
|---|---|---:|---|
| fresh-20261009T065028-cn-688012 | 0869d7f8d018e3cad76336c36d1ce3aefef00b3fa22dc7bdcd0303c81f672e85 | 180 | partial / complete |
| fresh-20261009T065028-hk-00700 | 42e44ef0c5631d2cb7cac28d3747c94ec6454faf810efe0e343801eeba114ed2 | 375 | partial / partial |
| fresh-20261009T065028-us-msft | 653fc57b29c48ececc018d848ec84f45f9514f2eb619567d38942182ff1cbc3f | 474 | partial / partial |

每个run的`handoffs/execution.json`已有MAIN实际交接。三个正式原生预测、Markdown、快照和注册表操作完成；这不能证明研究通过。HK/US早期authoring输入字节/少量时点留证缺口保留。manifest用于识别当时证据，不是许可证；不因MAIN计划文档新commit要求重签scope。

## 角色与调度

| 角色 | 独立agent | 独占输出 | 当前安排 |
|---|---|---|---|
| storage | /root/fresh_storage_reviewer | 每run `roles/storage/`、`reports/storage.json/.md` | CN已完成7 findings；后续空槽followup补HK/US |
| fetch | /root/fresh_fetch_reviewer | 每run `roles/fetch/`、`reports/fetch.json/.md` | 三家公司逐个审查 |
| process | /root/fresh_process_reviewer | 每run `roles/process/`、`reports/process.json/.md` | 三家公司逐个审查 |
| analyst | /root/fresh_analyst_reviewer | 每run `roles/analyst/`、`reports/analyst.json/.md` | CN storage释放槽后已实际启动，覆盖三家公司 |

审查者读取实际安装的audit SKILL、workflow、artifact-contract和自己的review卡；不读其他人的初稿、不改execution、不兼任别的审查角色、不补跑执行冒充当时成功。原件通过公共接口只读打开，本地复算写自己的角色目录。CodeGraph负责结构问题。每家公司均保留四个不同身份，不能用MAIN自评代替。

## 此节点的检查与后续

实测独占三家公司环境25,649,779B（24.46MiB），另有审计日志/索引32,351,421B（30.85MiB），两类分列；见[空间观察](footprint_observation.json)。没有扫描生产整湖或删除原件。此空间观察不是原件保存质量验收：CN STORAGE-003证实Lam HTML 305877B入库失败后未持久保留，已有财报原件可读与这一失败下载缺口必须分开声明。

1. 各角色依据自己的卡实际查阅全过程，包括失败和替代操作，JSON+Markdown字段按现有audit协议，不新增协议或签字。每个有影响的FAIL/BLOCKED/NOT_RUN关联finding；未知费用不当零，不捏造缺失历史输入字节。
2. 四份报告齐后MAIN一次运行已有audit check、实际读取四份正文，结构完整与质量结论分列。发现问题时needs_remediation/exit2是预期诊断，不能为了绿色删除finding。
3. 派独立编程专家归总三家公司问题，共用根因合并，但保留每run/role/issue→根因→责任包→测试映射。先交独立PWF施工包，初次不改代码；MAIN纳入当前主计划，避免另起冲突主线。
4. 优先进一步减少职责重复和错误阻断：区分源身份/期间/真实字节资格与展示字段，调查语言locale、空/未trim标题、来源类别投影、metadata gap是否造成不相关材料连带拒绝。以实际失败和责任反例为依据，不能总开关关闭错公司/未来资料/损坏原文校验。
5. 同时调查年度模型截断、ET请求/凭证传播、长物理文件名、DOCX/电话会HTML、敏感性依赖DAG与derived重算/量纲、强输出foundation引用遗漏及可恢复authoring历史。已支持的替代模型不算原缺陷修复。
6. 只在共用修复与真实公司复验的大节点验收；随后新三家公司泛化，最后冻结NVDA与公司池loop。当前未启动第二组、未宣称原三家研究全绿。

## 审批清理边界

已清理的项目重复授权见[结果](../permission_residue_cleanup/CLOSEOUT.md)。用户永久授权、既有模型/预算配置沿用，不逐材料/供应商再问许可。平台托管自动审批不受仓库控制，项目没有改写或绕过它；API密钥认证、实际套餐/能力与预算也不冒充人工审批。原件保护和用户要求的四路大节点质量审查继续承担各自职责。

## 审查过程的实际记录卫生事故

fetch reviewer一次读取ET config全文，原生工具输出含mimo_api_key/minimax_api_key/deepseek_api_key。本地仅作布尔核实：三字段present且非明确占位符，suspected_actual_credential_unverified，未网络认证。值不写入本计划/报告；原chunk_id=7eb7d0已进入平台工具历史/模型上下文，不能称未暴露。reviewer声明没有另发vendor/site、没有复制到本地报告，无法据此声称平台记录已删除。

脱敏事件：`C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/fresh-20261009T065028-cn-688012/roles/fetch/reviewer-sensitive-output-incident.json`。MAIN已通知用户建议更换三项密钥，未擅改配置/旋转密钥。后续只输出明确白名单非敏感字段与presence；专家须调查是否已有安全配置诊断入口可复用，修复诊断方法，不能把reviewer自身失误归为executor/公司数据错误或新增人工许可。
