# 来源准备根修：已验收，正常发布后执行 E

A/B/C/D工程与独立大节点完成：295P/157.53秒、397源mypy、ruff，独立19P/2.39秒/0OPEN，稳定11文件raw/LF已封存。真实本地冷启动ready，002643/IR，published未知，0下载/复制/POST。详见[source-preparation/README.md](source-preparation/README.md)。旧a6fea精确CI41000149392成功；新源码需观察自己的CI。

下一步 E：正常提交推送后使用本机 `.planning/source-description-20261030/prepared-cn-ir-summary-v4.json` 与 `cn-ir-development-gold-v3.json`，以canonical phase_c_runner运行 **real-summary-v2**。保持v1 NOT_RUN不可覆盖。参数沿用summary-preflight/RUN_NEXT.md，只把output从v1改v2；registered_readonly、0.9.0、reading-model-input/4、activation-recovery、consumer-projects均保留。实际配置MiMo，单次上限50k tokens/$0.05，母账不重置；不设置W21可选runtime环境变量。8个实际sent-source gold须在POST前全支持。来源prepared服务自动验证，不在上层手写身份或发布日期。

成功后审查实际自然语言claim（原语言/时态/主体/否定/数字单位），验证持久response、activation held/resume与跨run缓存0新增POST；FF复用0下载、RF只读consumer不等同实际预测采用，后者与八步公司loop继续OPEN。失败则记录准确阶段、实际花费与未知费用，按根因修复，不重复整批、不提高预算、不按公司补词。

后续重要回归检查：新入库自动准备而非裸query；内在文种与request顺序无关；partial scope只可证明不相关，不能冒充正向完整期次；法定名/跨行标题与引用区别；活动日不补发布日期。以后继续跨市场/IPO/增发/可转债元数据样本，但不借此拖延当前真实摘要。不碰W21三runtime/作者工区，不新增上层PDF抽取或第二套任务数据库。
