# PDF/TXT版本与宿主环境夹具解耦

原CI41019504113失败33项；W21合并CI41020271499失败34项，新增1项SYSTEMROOT宿主假设。不是远端网络或SDK运行故障：lint、类型检查和安装已成功，具体失败均有公开annotations及本地复现。

- 英文TXT历史line layout测试曾把PDF默认版本当TXT版本；独立pin其旧TXT1.1，保留paragraph1/旧1.0回放和全部经营正负对照。
- verify夹具解析TXT实际0.4却填写PDF默认版本；现在metadata取实际parsed unit的producer，拒错与字节绑定断言保持。
- 原raw generation测试测历史wire shape，但未冻结producer；当前默认1.2期望与注释相符。真正历史版本回放测试不改。
- W21环境allowlist测试不应假设Linux有SYSTEMROOT；显式提供PATH与SYSTEMROOT，保留原断言并加精确值匹配，未制造生产环境变量。
- pre-commit只做静态检查；pre-push宽影响面采用固定烟测，因此此前未覆盖这3组。只给现有回归清单补3个具体节点，不启动整模块或全仓。原清单、超时180秒/affected cap32均不改，清单约束31→34；元测试+代表节点9P/1.70秒。

最终失败相关4模块113P/4.15秒，W21两模块20P/2.57秒，ruff通过；两位独审覆盖稳定6文件raw/LF SHA、0OPEN。此为CI夹具/轻量回归清单修复，无生产行为改动。两次旧远端失败保留，修复提交的精确CI必须另观察，不能借旧绿。

W21工程1e4e9eb5已经合并推送（198P、pre-push158P/25.16秒），canonical SDK C2仍OPEN。真实摘要v3的语义4OPEN、FF/RF非期次SourceRef复用继续按SUMMARY_QUALITY_NEXT推进；本节点无新模型/下载/SDK。
