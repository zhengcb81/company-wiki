# 有限来源命题frame组件独审（尚未接线）

结论：**PASS_PURE_UNWIRED_COMPONENT，0 OPEN**，仅绑定assertion_frames.py及其永久单测。最终 **37P / 0F / 0skip / 1.42秒**，ruff两路径、mypy单源通过。前次28P/33P/36P是中间版本，不相加。

ROOT初始繁体needle断言揭示API语义不清：source经过matching_reading_text会转简体，因此字段明确改为matching_text。它是规范化的局部分句视图，不是原文quote或字节定位；原span/rawsource/locator始终权威，不为适应测试更改normalizer，也不复制多份raw段落。project_condition只保留有限条件marker，不重复其整个后果描述。

审查修复：

- according-to只有实际后续逗号分句、且是来源短语时才作为prefix；无逗号的整句保留，不能被贪婪regex吞掉。限定未知语法不推断。
- 显式同主体并列predicate可继承；and Gamma/并乙方这类新主体不能借前述归属。并且/and also真正同主体延续仍保留，跨句/分号重置。
- 问句和主导模板/准则说明不声明经营状态；持续开发的否定不当观察进行。capacity必须有实际数量表达，单独会计/折旧词不建立产能量。繁体量词、千分逗号/小数保持规范化匹配边界。
- 项目范围由本地链记录，只有明确项目回指或无主语capacity/条件分句延续，独立项目/其他部门重置；二期条件不能加给一期产能。现有/已投产阶段在同链中保留；not yet/has not been/will be commissioned不能变已有产能。

RED保留：initial-api-red包含字段迁移期失败，不宣称全部为语义缺陷；scope-red为迁移后12F/16P；额外真实反例commissioning-red为3F。最终37P证明本有限组件的固定行为，不代表通用NLI或完整语言分析。

**没有生产接线，没有修改/4、/5或已录制/6的历史assessment解释，没有调用模型/下载/原件解析，也未修改PWF。真实3P2问题、新摘要保真、RF实际采用和完整公司循环仍由ROOT继续；不能用本节点PASS代签。**

当前2文件raw/LF SHA见seal.json；写后复查一致。


## 真实support回放后的裸项目回指补查（最新）

ROOT在保存的实际support重放发现：前述建设项目→该项目产能→“项目建成后”没有接为同链，数量阶段虽正确、条件却丢失。先补非公司/产品中英同构2RED和5个独立主体/链断开负例；再仅扩大显式项目回指语法：活动同项目链中，裸“项目+建成/投产/完成/获批后”及“the project+after/upon/following completion”可衔接。项目乙、另一项目、project Beta、another project仍新链；独立分句中断后不能回跳。没有全盘放宽PROJECT，也没有公司名/产品/数值词库。

最新 **44P / 0F / 0skip / 2.16秒**，ruff两路径及mypy单源通过；前37P不相加。当前两个文件seal重新绑定且写后稳定。ROOT的assertion-frames-real-r1.json保持旧结果，未改写为PASS；它不是原support全文，因此本独审没有拼接旧frame冒充原文重放，ROOT可从保存support再验证。

仍是未接生产的有限组件，不签真实3P2已修、新模型摘要保真或RF实际采用。
