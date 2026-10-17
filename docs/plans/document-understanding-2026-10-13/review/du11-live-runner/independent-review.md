# DU11 唯一 Phase C runner 升级独立审查

审查员 `/root/du10_et_reception_review`，与作者/ROOT实现人员不同。**PASS，零未决问题**，仅覆盖 `source-freeze.json` 绑定的三份测试工具文件。三份实际SHA与freeze精确一致，最终提交可按这些源SHA回填commit，不要求文档自引用再开审查。

readonly分支使用既有source owner：当前config解析roots，只登记明确relative original group到owned catalog，再query/open/describe验证；不复制原件、不导入伪造原件、不补生产sidecar或元数据。仅临时config/catalog_dir被写，生产config/原件指纹保护，未实例化生产catalog数据库。实际metadata无法形成合法来源时，ReadonlySourceGap明确NOT_RUN，launcher前停止且0POST。

默认仍为历史0.9→0.8；显式单0.9将comparison_scope标为single_selector_no_paired_improvement_claim，并采用current_exact_ref证明，不冒充legacy之后的历史引用或paired改善。flags为增量，模型/费用客户端、AUTO保留/结算与母账unknown/FXhold路径沿用既有实现；normal same-run/cross-run零POST与精确Ref断言保留。

独立只运行四个快控制：只读登记同字节且只显式group、版本flags、metadata gap零模型、母账unknown/原生attempt去重。**4 PASS/7.03s，exit0**。owned temp及仓内插件重定位的pytest temp均确认删除，无外部网络、模型、密钥或真实生产原件读取。第一次外层输出遇GBK打印编码异常，且未保存returncode/XML，因此没有宣称那次pytest通过；仅为得到可读收据重跑同四个快测，过程已记录在JSON。

原最终XML实读为9项、0失败、0错误、0跳过；完整测试收据三文件前后SHA均等于freeze。其中single0.9真实本机fixture lifecycle已覆盖same/crossresume与Ref，本审查沿用有效收据，没有重跑该长案例。原件/生产DB保全与缺metadata反控也在该精确版本内。

该工具仍是明确prepared三样本的benchmark，未变成任意公司通用采集API。本PASS不代表真实供应商质量、PDF完整阅读或总体PWF完结。ROOT当前真实parse→select同2M余额耗尽、0span问题仍OPEN；本工具升级不能覆盖该生产C缺口，也没有提高任何付费预算或放宽权限。
