# 精确CI41056460382只读根因诊断

结论：**根因已本机确认，修复尚未由本审查实施**。远端head为bf58769b6287b5b6f268ce5bccbd619fb2061943，Unit tests失败；ruff、src mypy、compile/config都成功。不是timeout，也不是Node20/Ubuntu迁移警告所致。

公开check annotations给出仅两个失败：test_narrative_scoped_runtime::test_unknown_projection_does_not_fall_back[version2]和[version3]，TypeError。其参数分别为[]和{}。公开job日志API403；没有提取或读取任何Git/账户凭证，annotations和本地精确复现已足以定位。

本机Python3.13.9仅运行既有四参数节点，**2P/2F/6.53秒**；远端Python3.12失败完全同形：runtime.build_model_request先调用scoped_protocol_for_projection，后者在narrative_summary_protocols.py:41直接_BY_PROJECTION.get(version)，list/dict不可hash，提前抛TypeError。旧公共入口原本应以ModelResponseError(PROJECTION)拒绝这些非法版本，因此测试是正确的，不能删除或改为接受TypeError。真实合法/7执行不是这个失败的触发。

## 为什么本地绿仍漏到CI

pre-commit配置明确只做静态检查；mypy的str注解不等于运行时类型验证。atomic-push.log也明确resource dependency scope unknown，全部unit建议被有界快速push政策延期到CI；实际只跑固定161P/38.40秒，声称local_fast_pass/full_validation_pending，没有跑这条旧边界测试。新registry实现和新协议测试没有覆盖全部旧公共非法输入轴，这是大节点受影响域漏项，并非需要每次commit跑全仓。

## 给ROOT的TDD修法

1. 保留现在的四参数RED节点。统一在registry lookup责任层处理非字符串输入，不让dict.get先hash任意值。projection/request recognizer可以返回“没有匹配recipe”，再由原公共入口按原规则拒错；不能把非法输入改成默认有效协议。
2. 同类request/prompt lookup及bundle format的入口补有限错误形状对照，避免只对[]和{}两个具体值打补丁；旧/4、/5、/6 bytes不重标，新/7语义不下放到消费者重复实现。
3. 修后运行该精确节点、公共dispatch相关单元及atomic recipe/artifacts，正常static/push后看新head的精确CI。无需放大timeout、反复全量或新人工门禁；可在同一大节点的受影响域加入公共协议微合同。

本审查没有改生产源码、reader或三个已封工具路径，没有模型/下载/原件解析。原CI失败和focused-repro.log完整保留；review.json记录公开API、范围和实际文件SHA。

[远端失败](https://github.com/zhengcb81/company-wiki/actions/runs/41056460382)
