# C1完整CI失败：根因、修复与测试范围补全

失败代码提交：`87d39bbc5b3bacf59dfc6c3ead11665b7007e83e`；精确CI `40229110372`为failure，原状态保留。公开jobs/check-run annotations即可读取两个失败名，见`c1-ci-failure.json`，未提取凭证或绕过认证。

## 根因

两项均来自`tests/unit/du11_production/test_document_work_policy.py`：旧夹具覆写`NarrativeSelectHandler._parse_pdf/_run_selector`来观察共享预算。C1把PDF读取/选择职责下移到`PdfReading`后，正确生产路径不再调用这两个handler私有钩子；夹具观察字典为空，断言取`budget`报KeyError。原两项在本地原样复现，见`c1-ci-reproduction`。

这是重构后的测试观察边界过期；不是有证据的“预算被移除”。C1针对性预算/context替换测试已绿，但ROOT首轮只选`du11_production/test_pdf_production.py`而漏了同包work-policy测试。独审也没有纳入旧私有hook的全部使用者。这是验收范围遗漏，不能说本地或独审已覆盖完整生产包。

## 修复

仅迁移该夹具的观察位置：继承完整`PdfReading`，在`read`之后记账；`select`将真实bound selector包一层观察器后原样调用。真实PDF字节、native解析、同一个WorkBudget及两个原测试的全部断言保留：预算在parse→select不更换/不重置；partial诊断与实际limit/used一致；partial不能完整cache；修改work配置才使source cache失效，token/金额不影响source解释。

没有在生产代码加回旧handler分支，没有删测试、mock掉native/selector或放宽预算。源码职责继续单层封装。代码图与测试源码检查确认活动tests中仅此夹具覆写旧钩子；归档probe是历史记录，不改写当时证据。

完整`tests/unit/du11_production`＋新boundary＋source usability共**164 passed /18.15秒**（包括原2失败），临时目录恢复不存在，0网络/收费/下载。Ruff通过。最终独审见`c1-ci-independent-review.md/json`。

## 为什么hook没有全拦住；如何改进

pre-commit负责Ruff、mypy和host假设等便宜静态检查，本轮确实拦住了固定主机路径夹具，修为tmp_path后正常通过。pre-push fast反馈已如实声明350个受影响单测延期给CI，本地只跑154个契约smoke；它不是全量通过证明。

本次改进是**主线大节点测试包补全**：阅读owner/handler职责迁移时，完整跑既有`tests/unit/du11_production`，并按CodeGraph调用者/覆写者检查所有迁移接缝，再加对应carrier/runtime/generation回归；不能只挑同名PDF文件。此补充已写入C1/C2验收细则。不增加每次commit全量测试、不增加人工许可，不扩大CI复杂度。CI仍以完整unit suite发现未覆盖回归。

此文件发布时新提交/精确CI仍待观察；不能把旧失败改成success。后续通过收据由`c1-publication-ci.json`与CURRENT_STATUS记录精确新SHA。
