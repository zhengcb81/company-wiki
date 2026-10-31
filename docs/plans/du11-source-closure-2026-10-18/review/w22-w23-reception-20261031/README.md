# W22/W23 全部交付 ROOT 最终验收（2026-10-31）

**工程已并线推送946537d0；W23真实比较需返修。** 新增小问题全部由ROOT在隔离工区修复，未把小问题发回作者。唯一总入口仍CURRENT_STATUS.md/json，本次不表示全PWF或公司loop完成。

| 包 | ROOT结论 | 主证据 |
|---|---|---|
| W22-CWP-ATOMIC-IO | 工程接收、修复后交叉独审PASS、并线发布 | [独审](atomic-review.md)、[交叉审](atomic-cross-review.md) |
| W22-PDF-DEPLOY | 工程接收、修复后交叉独审PASS、并线发布 | [独审](pdf-review.md)、[交叉审](pdf-cross-review.md) |
| W23-XIAOMI-OCR | 工具工程修复后接收并线；实证CHANGES_REQUESTED/PARTIAL | [独审](ocr-review.md)、[返修卡](../../harness_lanes/20261031/W23-OCR-R1.md) |

精确提交、资源/清理、旧包状态及CI最近观察见[summary.json](summary.json)，最终代码与Git LF字节匹配见[绑定](final-code-bindings.json)。运行时CI最近观察in_progress，未写成已绿：[CI41238915399](https://github.com/zhengcb81/company-wiki/actions/runs/41238915399)。

## 直接修复的小问题

ATOMIC：深cwd短相对路径、Win32 UTF16长度、3.10异常保留、probe长树清理、相对TEMP归一、Windows实际scratch<=60且有限fallback，以及POSIX测试表示。保留同目录exclusive stage、现有有限替换重试、fast目标/timeout/退出码政策；无合格短根就具体有界失败，不假装任意深根可成功。

PDF：拒绝含已证缺项的部署plan和代码身份漂移；所有目标/恢复/receipt写入不沿目录alias越界；config只写owned目标；scaffold存在、隔离与实际字节共同绑定，不能把垃圾python或换home后的环境当REUSED。合法环境和原SDK证据保留，无新人工授权链。正式部署只读实核36127项samefile/size、18项源SHA、0reparse；旧两页真实enhanced/accepted2有效，但新工具没有改写旧marker或重跑SDK，真实文档C2和M8业务召回继续属主线。

OCR工具：统一CLI实际接隔离runner、父watchdog、真实代码/模型/precision身份、指标分母/币种/错页、跨两新进程持久缓存0重复推理、显式流式F32转换、轻量CI import隔离、3.10及UTF8子进程兼容。最终静态检查还清理未使用导入；不改历史raw/旧gold/作者工区。

## 必须返修的大问题

原OCR试验存在600s请求而非180s、已记录累计约2471.8s且尚有诊断、实际参数与旧manifest不符、holdout被pilot用过、逐页事实/条件与总表不一致。小米确有真实执行，488/488 tensor存储值精确零扩展也独立验证，但不证明计算等价；探索性结果保留，不据此宣布模型无效或全面替代。

[W23-OCR-R1](../../harness_lanes/20261031/W23-OCR-R1.md)只补累计campaign、约6新页/新gold与未曝光验证、逐页完整分母和真正独立终审。新工区company-wiki-w23-xiaomi-ocr-r1已就位，模型从原资产只读复用、不复制、不切生产。READY_TO_DISPATCH不表示已开跑。

## 测试与证据边界

ROOT新增反例合跑 **35P/3.20秒**，最后OCR编码/兼容窄包14P/1.61秒无warning；正常pre-push **167P/37.23秒**。各独审较早域含47P/1S、PDF88P及后续48P、OCR58P与最终17P等，范围/版本有区别且重叠，不相加成一次全量验收。新增最终代码已ruff通过、atomic两source mypy通过；没有新SDK/模型调用、收费请求或原件下载。Linux/原生Python3.10/真实UNC未本机执行，明确NOT_RUN，不用Windows绿测代签。

原子与部署都有独立中性RED→GREEN和交叉审查；ROOT再审收敛补丁。OCR最后UTC/UTF8和未用导入增量由ROOT修复并以fresh process/静态检查收尾；所有最终Git源码字节已封存。源日志在ROOT自有.planning/w22-w23-reception-20261031，本目录仅小摘要/必要日志，无模型/env/逐页图大副本。

## 盘点、保护与下一步

最新三个作者HEAD分别d19bda04、dc423843、a517213c，均匹配远端作者分支。作者树只读；W23.w23_cache仍是显式资产。ROOT M8/hook的开始/结束SHA相等，原件/config及其他仓WIP不变。[测试清理](root-cleanup.json)确认ROOT owned scratch恢复不存在；超长非BMP树清理使用经验证的扩展路径。作者PDF暖缓存约87MB未在原handoff列全，本次披露并保留，不擅改作者工区。

两份一次性未选全量发现清单共6280282B不再物化主线，已选manifest/gold/raw和作者Git历史仍保留；这是避免主线新增，不夸称全磁盘释放。

[较早三个独立仓盘点](older-accepted-branches.json)：IR/QA-RAG/MeetingConverter原交付已验收，但仍未进入各自main/master；保留原维护边界与明确并线待办，不写成已发布。W20 RF/FF与W21工程已以实际祖先确认，不重开旧全量验收。

**下一步：回M8来源遗漏/限定共因根修→真实摘要→缓存恢复→RF实际采用。** R1可交独立harness并行；主线不再等小问题返工，不新增小节点签收。
