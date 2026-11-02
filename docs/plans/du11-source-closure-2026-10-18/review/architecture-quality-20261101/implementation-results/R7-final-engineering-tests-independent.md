# 最终工程测试与冷诊断：独立大节点审查

**两个scope均PASS。** 本审不是作者，没有自审另一条本人修改的3个handler/source-facts测试，也没有改产品、工具、测试、Git或主PWF。7个独立控制全通过，1.385s。精确5＋2路径SHA及原始证据见同名JSON。

## 工程测试整理

- 对真实base Git5文件逐一提取旧test定义：能力去向表覆盖全部，目标函数真实存在，没有新增skip/xfail。3份现存文件实际只收集106case，未执行106或4个真Git E2E。
- 独立docs/runtime/config/unknown/未知范围反控证明docs0，其余同DAILY9只执行一次，失败31原样返回，没有AST扫描和伪GREEN。
- CI Unit分离及22非Unit目标、6个OCR资源检查保留。180/600真实deadline、全Unit双worker与实际临时目录清理仍在。
- optional AST传递导入、40/64位SHA多ref范围union保留。实际sh执行缺runner hook仍拒。tool/CI/hook冻结字节未变；4个真Git场景静态检查保留，没有重跑。

## 冷诊断重跑

同一REVISION下，fakechild第一次抛真实ChildTimeout，第二次显式请求成功，各有fresh attempt和独立收据；旧根marker、旧根receipt及旧attempt都保持原字节。真实选定profile的名称/hash记录正确。CPU、内存、流、文档timeout与显式deadline不变，两份scratch均删除。没有调用真实SDK/模型，也不声称测得冷启动性能改善。

## 验收边界与清理

不把collect106冒作106执行全绿，不重作者全组，也不签完整CI/H1。两个scope独立结论均可交ROOT正常发布。自有目录初始不存在，测试源码/所有观察已保存到JSON后仅清本目录；最终cleanup字段记录实测恢复状态。
