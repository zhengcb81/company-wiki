# Progress

- 2026-10-09：建立本次优先CI调查子包，主PWF继续为原三家公司研究与根因修复；三名独立reviewer仍运行，不改其证据/报告。
- 已核对当前CWP工作树干净和最新提交；只读恢复已有planning-with-files与主PWF上下文。下一步远端run取证和hooks差异盘点。
- 已取得5真实失败run/job/annotations；RF相邻15run无失败。旧日志取证和本次REST403分开列；FF3945/afbef两个ratchet分别exact blob正常OS复现，697修复exact2PASS。
- CWP正常OS基线2299PASS/128.21秒；sandbox子进程/event-loop假失败已中断，不归为CI代码缺陷。新53集中责任PASS/1.17秒；独立审查4RED→GREEN，历史4范围均覆盖失败责任unit，CI完整unit不缩小。
- FF独占397ec0ee已验收并正常fast-forward main；549PASS/4SKIP/78subtests/59.70秒，未跟踪FMP key保留。正常push在运行；CWP准备commit/push。本包还未宣称发布最终绿。
- 已发布CWP d1ce50ee：正常commit5.76s，真正pre-push一次2346PASS113.39s，远端37910840899 SUCCESS。FF普通397hook发现少跑v2 E2E，补公共config loader定位后23d25644真正hook553PASS/4明确SKIP/78subtests/59.80s，远端37911571894 SUCCESS。两仓均主线已推，不旁路hooks。
- 四个owned测试根123746526B与FF独占worktree恢复不存在；其他历史worktree/WIP/key/原件不动。调查closed，主goal active，下一步原三家64finding独立专家共因PWF。
