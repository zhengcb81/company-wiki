# R7 跨仓逐项独立核对

结论：**原RF-01–05和最终跨仓SW八项的已知工程整改均已落实，未查到实质遗漏。真实公司验收仍未完成。** 本轮只读当前canonical，不重测试、不改Git/PWF/原件/配置/部署，不读FF密钥。

## 逐项矩阵

| ID | 状态 | 当前核对与主要责任 |
|---|---|---|
| RF-01 | ENGINEERING_COMPLETE | BODY_LIMIT/RECEIPT_LIMIT/REQUEST_LIMIT/READING_CONTEXT_LIMIT无默认表示帽；reader按已绑定narrative_ref.byte_size及显式调用预算限制实际读取，deadline/进程回收保留；core ref/source/support/context shape仍严格。 |
| RF-02 | ENGINEERING_COMPLETE | proof MAX_BYTES=None；摘录以非空、完整原文hash及closure/anchor/context绑定为准，不裁切；采用理由不再固定字符许可，formula/claim/参数依赖仍验。 |
| RF-03 | ENGINEERING_COMPLETE | 共享review_observation产生absent/unavailable/not_reviewed；optional损坏不升级已审、不抹主状态；真实source身份、wire核心合同、支持/上下文分区和内容绑定不因诊断缺失而取消。 |
| RF-04 | ENGINEERING_COMPLETE | _append只写自含publication-index/2行，不读全历史；OSError记录unavailable诊断而不否决有效结果；_clear_read_only为退休空兼容函数；显式audit/lookup可发现坏旧链；rebuild先验输入；真实声称签名仍验证。 |
| RF-05 | ENGINEERING_COMPLETE | reader返回verify_original_read实际构造的immutable bytes/serialized metadata；preparation投给同owner composer，公开raw builder仍verify；历史tuple注入走raw分支；prepare_forecast不再相邻重验；NarrativeContext.to_dict副本隔离。 |
| FF-CURRENT | KEPT_BY_REASON | 当前v2下载意图由请求表达；legacy authorization仅可选provider/accession/资源scope，expiry/hash不签许可；矛盾显式意图仍报request_error以免同请求两种行为。未发现正常使用前强制Git clean/全套CI/人工签收。 |
| SW-INV-QUOTE | ENGINEERING_COMPLETE | 移除唯一固定len范围；非空、excerpt SHA、capture/source/target/日期/币种单位仍独立验证；无截断。 |
| SW-RF-QUOTES | ENGINEERING_COMPLETE | target明确非空excerpt；actual claim保非空及text SHA，不再按长度拒；measurement/currency/unit/control period及真实数值重算保留。 |
| SW-RF-DRIVERS | ENGINEERING_COMPLETE | driver/evidence只要求非空，不再上限10；unique ID、已知source/claim、因果参数/segment归属、排名与sum/reconciliation照常验证。 |
| SW-FF-CONFIG | ENGINEERING_COMPLETE | 统一reader完整stream.read再严格UTF8/JSON对象及root路径解析；无64KiB许可；坏编码/实际不可读/物理root仍报config_error。原审先保、后扫查证实删除的演进明确，非遗漏。 |
| SW-LOCAL-DIAGNOSTICS | ENGINEERING_COMPLETE | FF/RF以迭代有限/无环/pathless JSON观察并复制，不按表示规模拒；坏optional附注剔除保blocked主因/计数；usage解析捕获RecursionError，request/schema/complete/counters真实绑定，坏值None/None/False，不补0或重发付费。 |
| SW-RF-AVAILABILITY-TEXT | ENGINEERING_COMPLETE | 移除字符上限，保非空trim/control字符、pathless证据ref、同源SHA、basis/date/as-of语义；不是取消source时点校验。 |
| SW-E2E-FIXTURE-PERMIT | ENGINEERING_COMPLETE | 显式generator从原embedded input真实canonical生成合法3.7/4.3.0/unattested；355共享numeric/12经济golden未变；去index预登记，双CLI及公开中间产物3–8检查真实调用；update-golden拒经济漂移；新独立run不枚举历史目录。 |
| SW-INV-REPEAT | ENGINEERING_COMPLETE | 去三处立即重复validate_revenue_forecast；revenue_reference仍完整强验；legacy无reference分支保校验；独立公开validate_execution读取仍重算全state，不新skip flag。 |
| INV-CONSUMER | ENGINEERING_COMPLETE | 注册/签名观测不作许可；current结果仍走validate_published_forecast完整embedded-input重算，legacy真实兼容读取；unattested不拒、不伪签；删除caller opt-out授权参数。 |
| INV-HOOK | ENGINEERING_COMPLETE | core.hooksPath当前.githooks；commit git show :0读取index真实bytes，syntax+Ruff自有临时树；push Ruff+固定adapter/三跳smoke，真实120s/非零；无自动部署/全套E2E。RF日常12+CI41、FF11+CI40同类分离也核对。 |
| INV-INSTALL | ENGINEERING_COMPLETE | --file定点选择、物理alias去重、source alias拒回写旧snapshot、sameSHA零写、逐文件atomic/readback、partial如实返回；显式旧full/check兼容但不被hook隐式调用。 |
| RETAINED-RESOURCES | KEPT_BY_REASON | 保真实流式32MiB transport边界、共享deadline/own进程回收、用户请求资源及未知paid恢复；RF叙述reader以绑定byte_size/显式max参数计实际读取，不是嵌套JSON固定许可。 |
| RETAINED-CORRECTNESS | KEPT_BY_REASON | 这些定义材料归属与数值事实，不是manual许可。未知语义/未完整处理不升级事实；声称host_signed须真验但未配置不要求签名；比较2对象/敏感度2不同值是领域维度，不是报告规模帽。 |
| RETAINED-FORMULA | KEPT_BY_REASON | 当前仍500字符，另保AST节点白名单、已知变量、除0、指数安全范围、finite结果。若将来需长公式，改显式AST/work预算另行设计，不能无替代删实际计算边界；不是本轮quote cap漏删。 |
| RETAINED-CREDENTIAL | KEPT_BY_REASON | 读credential4097探测、4096上限及非空可打印ASCII检查为小secret scalar；仅审代码，未读FMP文件或环境secret值；密钥不得进提示/报告。 |
| RETAINED-LEGACY-DIAGNOSTICS | KEPT_BY_REASON | 正常forecast/preparation无processed_artifact_canary调用；owned manifest digest仅--version分支；旧registry历史audit显式可拒坏链但不影响正常新artifact。legacy authorization/expiry兼容已在FF-CURRENT逐项核。 |
| CROSS-DEPLOYMENT | ENGINEERING_COMPLETE | 独立按原RF18runtime+3技能说明与后续RF5runtime+2说明的并集28、FF18 runtime、Invest3runtime+1合同说明计50文件；.agents/.claude/.codex三份各自SHA，共150/150和当前canonical一致；未读配置值。 |
| REAL-C-AND-COMPANY-LOOP | REAL_ACCEPTANCE_OPEN | final-closure/CURRENT_STATUS明确T4 parent-chain P2、新runtime真实C、R4六问题与完整公司loop仍OPEN。先根修source父链，再按原90s/16M/112真实H1；之后真实摘要/paid恢复/同跨run零重复/同artifact RF实际采用。此审计不替代这些验收。 |

每项的原要求、当前文件与符号、保留测试、独审版本、发布commit和部署归属，见同名JSON。共24项：工程完成17，按理由保留6，真实验收开放1，MISSING=0。

## 当前版本与部署

- RF `e44c7e9717c05346086e5ec07bc1f30373f8279f`、FF `350cb39dad8a1116d76fd44824fe353ae210d384`、Invest `9b68cc9b9bac194ede4881453f7706528bc18add`与R7-final-closure的精确CI来源一致。
- 独立逐字节比对：RF28文件、FF18、Invest4，共50个已知R7运行/技能说明文件；`.agents/.claude/.codex`三个根合计**150/150一致**。没有运行安装器、读配置值或修改RF四份WIP；四份最终SHA仍与原记录一致。
- RF初审29文件现在28/29一致，唯一变化是availability旧2048字oracle已被后续CI跟进修正并覆盖。Invest11/11与FF daily5/5仍精确匹配各自独审版本。没有拿旧收据冒签新的字节。
- 原FF64KiB配置帽、128KiB附注最初暂保，最终扫查有证据后已移除；矩阵明确这次状态演进，不把旧审计文字当现状。

## 保留和未完成

保留真实字节/SHA/身份/期间/as-of、引用与货币单位/公式重算、实际下载/HTTP/工作/费用/deadline预算和被声明签名的真实性。公式500是受限AST计算边界、credential4096是小secret标量读取，不等于自然语言摘录许可；若需扩展须改其真实资源owner。显式canary/audit/version工具和legacy兼容不算正常使用许可。

T4父链P2、新真实C、R4六项及完整公司loop仍**REAL_ACCEPTANCE_OPEN**。合成/CI/安装字节通过不能签这些产品验收完成。

另有两处非阻断注释仍沿用旧措辞（registry docstring、RF hook同表注释），已在JSON列明；当前控制流没有对应许可，不因此重启门禁。无临时目录创建，仅新增本报告两文件。

