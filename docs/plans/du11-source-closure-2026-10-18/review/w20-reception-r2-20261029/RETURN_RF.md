# W20-RF-ADOPTION 第二轮定点补完（2026-10-29）

本文件替代上轮RETURN_RF作为现在的返工入口；沿同一原卡、同一工区和分支继续，不重做已关闭内容，不另开新任务。ROOT未并线，主线公司循环仍暂停。

- 工区：`C:/Users/郑曾波/Projects/revenue-forecast-w20-adoption`
- 分支：`codex/w20-rf-adoption-20261028`
- 本轮HEAD：`b2979af6522dd4deb9d493f228f24c52a6aa03a5`，代码`e4657377`。
- 原PWF：`docs/plans/w20-rf-adoption-2026-10-28/`，PLAN_ID不变。
- 必读：[独立报告](rf-review.md)、[机器报告](rf-review.json)、[同源材料错配实证](rf-evidence/material_probe.py)、[坏压缩流实证](rf-evidence/additional_probe.py)，以及原卡construction_card.md。

## 已关闭，保留成果

异源借哈希和不存在source_id已拒；同span两年采用路径聚合正确；解压大小限制生效。真实/3多父在refs[1]、缺hash仍宽松used并记unknown、错误已提供hash拒绝均通过。37项交付短测10.95秒全绿。不退回固定首父，不增加hash必填或人工门禁。

## 尚需修复

**RF-R2-01/P1，原R1已知材料边尚不完整。** 对同份合法source分别真实consume：A的claim是CEO问答，B的claim是表格，二者local claim_id/parameter_id/原件hash/公式相同。A真实forecast配B真实receipt，工具仍把B span判used；A locator与excerpt_sha明确指向另一材料。

共同receipt resolver应按现有source_narrative_context consume生成合同核对应claim的实际材料（locator、excerpt/excerpt_sha及已有parent/source映射），不能只核原件hash和ID存在。legacy沿实际raw_text/locator；投影沿实际source_locator/父。缺可选字段保持unknown，不造新许可。这里核的是该adapter一次新建唯一claim的原始材料身份，不是要求研究报告的所有support都与quote逐字相同，不禁止同参数或同claim合法多证据。

用不变量测试，而非再加一个CEO字符串补丁：同capture两种span、两次真实consume→forecast收据交换、有已声明locator或excerptSHA矛盾、合法多证据/多路径、/3多父及缺可选字段各有正反对照。一次建立索引，共用解析owner，不重复遍历整库。

**RF-R2-02/P2，原解压可靠性遗漏。** 19字节有效gzip头+坏DEFLATE抛zlib.error，真实CLI exit1 traceback。将库自身该异常归一到现有input_decompress_failed，保持exit2和不留半输出；不捕所有异常吞bug、不提高额度。新19B反例、正常/恰好limit/超limit/截断短测覆盖同一错误边界。

## 收尾

原allowlist/隔离约定继续，只修共同owner及必要测试/文档。先保存有效RED，再运行相关短包/有限真实deterministic CLI和新增反例，不重跑全仓/新付费预测。测试根恢复初态。progress的handoff文档SHA落后只顺手同步，不作为产品单独门禁。

最后调用真正独立agent核原卡、以上不变量、修复及兼容，范围内问题全部修复后更新同delivery/handoff.md/json：最终源码commit/SHA、受测/受审版本、真实命令结果/清理/局限。旧审查/旧RED保留，本轮报告另存；正常commit/push原分支，不自行并主线/全局安装。然后交ROOT复验，无中间小节点签收。
