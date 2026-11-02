# RF/invest算术同根整改

状态：AUTHOR_IMPLEMENTED_FROZEN_PENDING_ROOT_INDEPENDENT_REVIEW。仅现有两个算术owner和各一专用测试，未动其他finance模块、配置、Git、全局副本或RF4份WIP。

移除500字符许可，不strip空白绕旧帽。两个API接受可选FormulaWorkBudget；默认None不制造新quota，显式account可跨多式累计。一次owner承担解析输入扫描及实际AST visit/evaluate工作，先预扣parse工作再调用真实ast.parse；迭代栈代递归，无另设depth/node/length顶帽。真正parser容量异常和非法实数算术仍稳定具名拒绝。两repo不互相import，不建跨仓包/签收/skip权限。

同一正反合同两边完全一致：修前各6F/14P，真实长式/600层一元/等价空白/缺工作账户失败；修后RF32P/0.41s（20共同case+12既有numeric/derived责任）、invest21P/0.33s（20共同case+1既有artifact）。保未知变量、NaN/Inf、非法节点/Call/Subscript/modulo、除零、幂范围与四类经济算术原值，派生参数真实重算仍通过。没有改旧expected或重跑整仓；旧full-result4.1.0 golden与当前engine不同，未用skip冒经济验证。

4文件Ruff通过，2个现有source的mypy --follow-imports=skip各通过。源码所有非算术前后缀与HEAD相同；RF80/invest10当前runtime对比只有各自算术文件改变。真实source/费用/输出预算和unknown paid/CAS不在本次改动内。相同测试合同SHA、4文件seal、所有RED/GREEN原日志/JUnit和静态输出在JSON。

临时测试/静态cache归本次初始absent的math-g3e218，清理收据后补JSON；无原件/模型/下载/收费。ROOT最后集中独审后正常发布，本作者不commit或安装。接下来ET单owner另写et-repair，不混签。
