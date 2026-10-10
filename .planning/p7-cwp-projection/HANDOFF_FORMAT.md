# 最小可复查交接格式

每卡只在自己的PWF目录交 **HANDOFF.md + handoff.json**。这是工作结果和测试证据，**不是授权或人工签收文件**。中央PWF只由MAIN归总，不要求逐小节点填写。

## HANDOFF.md

1. 结果：engineering_complete / partial，完成范围与仍须MAIN/真实研究的部分。
2. base、branch、精确delivery HEAD、实际改动文件和normal hooks结果。
3. 根因→正负控→实现→结果：RED/GREEN/E2E真实命令、exit、日志；计数有重叠不相加。
4. 对外API/default/opt-in/旧emitter的兼容和MAIN最小接线。
5. TEMP初始/恢复、原件/config/旧报告和ownerWIP保护；实际新增文件/字节和0外部费用。
6. 已有remote的branch/CI状态或no_remote/not_triggered；具体安装候选；未解决限制。

## handoff.json

见handoff.schema.json。路径相对自己PWF；交给用户/MAIN时给HANDOFF文件绝对路径。tests可将多测试放同一个责任日志，记录expected_exit_code，RED非0不能当GREEN。保护/cleanup的详细证据可一文件引用，不逐文件签名。

CI不是额外阻断器：记录passed/failed/pending/not_triggered/no_remote真实状态；failed必须列原因，不称engineering完成/已发布。发布/安装由MAIN接收后办理，外包不自行改主线或安装副本。

示例handoff.example.json明确example_only、全为合成样例，**不表示任何卡已实现或测试通过**。不得把示例delivery HEAD/测试日志当真实交付。

每次证据写入自动新建短attempt目录并独占创建；失败保留原日志。不得要求人手工备份后覆盖同名文件。日志不含密钥、全env或大原件；费用未知为null，下界不能标已知总费用。当前三卡默认0外部provider/model，不以执行harness自身的模型调用冒充项目供应商调用。
