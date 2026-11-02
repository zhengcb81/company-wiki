# R6当前交接 — 全面整改已恢复

唯一入口：[CURRENT_STATUS](CURRENT_STATUS.md)/json；选 `PLAN_ID=du11-source-closure-2026-10-18`、`PWF_PLAN_ROOT=docs/plans`。用户已恢复实施，不再执行历史暂停或再次 revert。细节和真实失败见 [R6-ROOT](review/architecture-quality-20261101/implementation-results/R6-ROOT.md)。

## 当前代码与所有权

- ROOT master：已FF到6b70394b，W23工具候选完整CI41363162079成功，尚待本次主线统一推送。生产src/config/依赖未因W23改变。
- ROOT自有 `tmp/architecture-r2`：`codex/architecture-rectification-r2-20261101`，修复745a72d3合最新master成为9f575810，正常push167P/47.74s；完整CI41364303788为22F，已开同owner R3返修，不并线。
- ROOT自有 `tmp/w23-r6`：`codex/architecture-w23-repair-20261101`，工具runtime ae438a32、独审和候选完整CI均过，6b70394b已本地并主线。旧作者工区不改源码；仅有精确PNG清理收据。
- ROOT唯一维护本PWF与集成；来源/消费者/W23作者均已STOP、独审已交报告。外来hook mode和历史未跟踪文件不stage、不清理。RF四WIP、Dayu/IQS/Dashboard不动。

## 下一步按此顺序

1. 先读R6-CI-r2.md/json的实际22F；以新的有界annotation完整分组定位，定点重现和共因修复；不能删除原断言、抬额度、加公司特判或退回跨层reader代理。
2. 当前只先正常发布完整CI已绿的W23工具和PWF；R3源码候选CI绿后再正常FF/merge到ROOT master，保护已有PWF/hook字节，正常commit/push当前进展并核新主线CI；不绕hooks、不取Git缓存凭证。不要再跑一遍本地全仓超时检查。
3. 实施既有T3：structure责任层统一编号完整句/闭引号判断，识别显式编号备注的长/换行局部scope，保留新备注主体引介。先去公司化RED，不能只删错边。具体9对原始unit及根因见R4-context-investigation.md。
4. 单次最终H1 source replay：沿本地schema2 runner/已冻结cases，原90s/16M/112不变，核12unit/111成员、9对真实view/member及正向scope引介。v1旧数量和v2公开合同失败不能代签最终。
5. 来源过后以独立catalog/AUTO引用既有原件做新版正式摘要、prepared中断/same/cross恢复和RF参数/公式/报告/snapshot实际采用，集中独审。两旧P1配置已absent，依C-preparation重建测试配置，不复制原PDF/旧DB、不改R3/R4封存。

## 已验收和不应重做的范围

消费者50P，独立7P+CF3稳定窗口1P；ROOT schema/offline关联72P/28.53s正常宿主；R2来源322P/15.65s、独立22P/16.84s；CI诊断17P及独审过；四种frozen Exception已根修。746P属于A1历史，随后发现新P2，R2不冒称重跑746。W23工具独审PASS，旧8页实验依然PARTIAL：真实总耗时null，1800秒合规、峰值/精度/生产适用性未证，X1历史失败保留，未切生产OCR/未重新推理。

## 环境、数据与余项

宿主Python `C:/Miniconda/python.exe -B -X utf8`。原子写测试/Git用获准正常host；Low sandbox下os.link WinError5会造paid响应不可用，已由同72域host全绿证实，不为此改CAS。独占sparse要完整工程src/tests/scripts/tools/config/.githooks/.github和确切gold夹具；--no-checkout后read-tree初始化索引，不能逐缺夹具打补丁或复制companies。

原件、生产配置、DB/WAL bytes+mtime保留；SHM仅same existence/size/SHA允许mtime同步。不可构造生产AutomationStore作只读观察。冻结R4：AUDIT runs/r1-20261021-cn-wuxi-apptec，attempt r1-remediation-04，585件64240251B，manifest75f2871b…c568不改。

预算按config10M/$20、公司150k/$1软目标；最近母账1965633tokens/762082microUSD估计，unknown8+prior7，本轮0收费调用。授权沿用，不新增人工签收/材料许可。RF957c6283 main已绿并定点部署；StockWiki381811e5本地master无历史remote，不冒推送。

ghost-formula/期间补集、W21真实增强、长文/US监管PDF/HK/RPO、固定八家和新泛化/连续三家clean仍OPEN。原生goal工具目前paused且无active resume接口；当前是最新用户授权的手动续接，不新建竞争目标或声称整体完成。
