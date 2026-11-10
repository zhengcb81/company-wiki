# DU11 完整付费响应耐久化独立审查

**工程PASS，可集成8文件；审查夹具NOT_CLEAN明确保留，真实C仍OPEN。**

## 受审范围

8文件实际SHA与冻结handoff全部一致，详见同名JSON。实读新byte port、caller、HTTP、runstore、migration、store重排入口及两类测试。原有AUTO只新增nullable pin列，复用内容寻址对象；没有第二库/账本/缓存，也未把response伪装visiblebundle。

HTTP在有限完整body读完后、envelope前耐久记录；outerbodySHA和finalcontentSHA分开。原request/body与model/adapter/prompt/size绑定。旧原attempt身份可留证不代表有今日发布lease；当前lease和冻结jobmembership负责重放/输出重开。unknown/missing/clipped/tamper不能触发盲POST，费用仍在原reservation；knownusage重放幂等，不给新attempt增provider预留。正输出/已成功/有效effect/运行中attempt禁止重排。未发现必须修复的runtime缺陷。

## 有限独立控制

直接调用真实owner＋合成fakeHTTP，未启动pytestsuite/socket/PDF：

1. paid→terminalfailure→原job重排→新lease→删合成key后重放：所有断言通过，fakePOST总1、reservation仍1、92tokens/费用不变、旧输出slot重开。
2. 最后追加的positive-output前置检查：failedpaidoperation合成10positivebytes，在retry事务即拒绝，jobstatus不变、fakePOST仍1。只读复核该夹具DB为known73input/19output/45microUSD/output10。

两个运行控制均完成断言到达收尾；**进程exit1仅来自reviewfixture清理**。首次独立probe缺自建子目录，在任何fakePOST前InvalidStorePathError；仅修审查夹具。复用作者168集中PASS、最终28PASS/9.06s及其1loopback恢复证据，不把最后增量冒称已包含在旧28中，也没有重复大矩阵。

## 清理边界（不得冒称全恢复）

遗留 `C:/Users/郑曾波/AppData/Local/Temp/du11-independent-paid-lij5od2g`，7文件/393369B，仅合成AUTO/对象。原因是审查夹具sqlite context未显式close，TemporaryDirectory退出时WinError32。进程结束后对已核对精确绝对Temp的PowerShell删除被平台policy拒绝，未改通道或再试。标记**NOT_CLEAN**；不是业务runtime失败，不影响这8文件功能PASS，也不谎称目录已恢复。无真实原件/config/密钥/生产DB。

## 后续仍OPEN

ROOT的默认factory/空间预检/terminalfailed恢复接线、审计终态压缩、正式sourcecard和真实供应商C不在这8文件PASS范围。durable前不可观测窗口仍unknown；未绑对象不能推断恢复；旧v4身份和账不改。ROOT可现在集成8文件精确字节，之后只对store.compaction新delta复核。
