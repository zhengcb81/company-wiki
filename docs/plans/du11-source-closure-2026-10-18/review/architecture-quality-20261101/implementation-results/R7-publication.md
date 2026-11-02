# R7发布与部署实际记录

CWP核心37＋工具30、RF29、ROOT17均经最终独审；发布跟进6文件增量独审10P后正常commit。CWP源码fee04ba4（正常hook75.076s，首次瞬时index锁消失后正常retry，没删锁）、RF runtime a922305a及main499d5ca3、invest a7812888。源SHA和外来hook bytes/mode保持；RF四WIP经全SHA校验保持，precommit对两JSON换行的恢复影响已按精确旧字节恢复，不猜内容或提交它们。

RF正常首次push689P1F1skip/84.924s暴露旧v1链oracle套在新v2索引；实际语义迁移保v1/真篡改反控，local固定12/CI原41文件完整保留。最终正常push成功：12P1.16s，总10.532s。不是no-verify，也不是从CI删除失败用例。

使用canonical --file安装器同步RF21与invest-core2文件到三根69逻辑目标；RF新增helper先部署，完整目标SHA核对，重复零写。6份公开config SHA保持，未知config/output无目录替换。三独立新进程只加载对应安装根代码，合成RF→invest通过且收入×1000后重哈希仍拒，未签不升级；禁所有网络，总1.387s。独立UUID测试目录恢复absent，原件/模型调用0。此为部署工程验收，不能代真实H1/摘要/恢复/公司研究。

CWP主PWF bundle与invest正常推送/精确远端CI正在收口；JSON保实际版本和部署全target/hash。旧失败、各阶段增量收据和真实C OPEN保留，不合称全仓一次全绿。
