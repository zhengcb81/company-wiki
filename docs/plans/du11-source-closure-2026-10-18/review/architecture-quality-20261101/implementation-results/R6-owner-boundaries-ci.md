# R6：剩余两项 owner 边界 CI 回归

状态：**作者短域验证通过，待 ROOT 独审与发布**。本次只修改 `tmp/architecture-r2` 的两个测试文件，生产源码、Git 索引、分支、主 PWF 均未修改；不声明其余 CI 失败已解决。

## 候选与范围

- 工区：`C:/Users/郑曾波/Projects/company-wiki/tmp/architecture-r2`。
- 基线 HEAD：`9f575810ca92620a6fb6ff63cfd326a5b9f076fa`；对应 ROOT 完整候选 CI `41364303788` 的 22 项失败摘要。
- 仅处理纯来源身份契约的新进程导入隔离，以及当前 partial reading inventory 不得命中缓存。
- 不触碰来源语义作者负责的 grammar/source_context/passage/business_policy/operating_states，也不触碰 ROOT 的 value-coverage marker 测试。

## RED 与责任归因

第一次在宿主 Python 3.13.9、显式 `PYTHONPATH=src;tests` 下只运行原两项：**1 failed / 1 passed，4.53s**。partial 测试返回 True；纯 DTO 导入通过。随后按 CI 的无 PYTHONPATH 环境重现原纯 DTO 单项：**1 failed，4.65s**，实际 stderr 是 `ModuleNotFoundError: No module named 'company_wiki.source_contract.source_version'`，并非证实 DTO 导入了 catalog。

1. **缓存测试 patch 仍绑定旧 owner。** 生产 `narrative_generation.current_reading_decision_matches` 已从 `source_catalog.narrative_decision_inventory` 获取实时 inventory，并在 comparator 前拒绝 `inventory_complete=False`。旧测试 patch `document_understanding.decision_inventory` 薄兼容 re-export，不能影响真实 composition owner，故注入的 partial 从未到达产品。将测试 import/patch target 迁至真实 source owner；保留 False 与 comparator 零调用断言，未增加生产代理。
2. **纯契约子进程未绑定待测树。** `tests/conftest.py` 修改的是 pytest 进程内 `sys.path`，并不会传给 `python -c` 子进程；CI 的 requirements 安装也不包含 editable package。原测试依赖宿主 PYTHONPATH/旧安装，因而平台环境能决定测到哪份代码。新 probe 以 `-I -S` 启动，并通过显式 argv 将本候选绝对 `src` 加入 `sys.path`，核对实际 module 文件。没有把 pure DTO 接回 catalog，也没有删除不导入 catalog 的断言。

## 保留与新增的反控

- 纯契约分别在 PYTHONPATH 缺失、PYTHONPATH 指向故意报错的其他 package 树时通过，确保测试对象是候选源码。
- probe 安装只读 import finder，任何 catalog 运行时 import 均失败；故意追加一次 catalog import 的负控证明该防线确实拒绝反向依赖。
- partial inventory 即使 comparator 被错误 stub 为 `same` 仍返回 False，且 comparator 不得被调用。
- complete inventory 必须到达 comparator，并保留相同的 dependencies/current 参数，避免错误地将“一律 cache miss”当作修复。
- 两文件既有可替换 narrow port、错误字节拒绝、缺/坏 digest、旧冻结 manifest、复用原文/发布证明等行为断言保留。

## GREEN

正常宿主最终命令（无 PYTHONPATH；显式沿用 pytest 退出码）：

```powershell
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
& C:/Miniconda/python.exe -B -X utf8 -m pytest tests/unit/test_source_contract_reader_port.py tests/unit/test_shared_reading_cache_precheck.py -q --disable-warnings --tb=short
exit $LASTEXITCODE
```

结果：**35 passed，27.16s，exit 0**。其中 source-contract 文件 5 项、cache-precheck 文件 30 项。此前一次 34 项均绿，但 shell 的环境恢复语句给了 exit 1；最终改为明确转发 pytest 退出码，并在新增 complete 正控后获得上述 exit 0，不把 wrapper 状态冒充产品失败。

```powershell
& C:/Miniconda/python.exe -B -X utf8 -m ruff check tests/unit/test_source_contract_reader_port.py tests/unit/test_shared_reading_cache_precheck.py
git diff --check -- tests/unit/test_source_contract_reader_port.py tests/unit/test_shared_reading_cache_precheck.py
```

两项均通过。未运行整仓、实际文档、下载、收费模型或生产配置/数据库操作。测试使用 pytest `tmp_path` fixture，但本次日志没有绑定专属 owned basetemp，也没有测试前目录不存在的证据；pytest 默认可能保留历史 basetemp，因此**未验证临时目录清理或测试目录恢复**。保留无法归属的临时文件，不猜测路径删除。下一轮应先明确 owned basetemp、记录初始状态，再按 containment 核验后仅清理该目录。

## 冻结文件 SHA-256

| 文件 | SHA-256 |
| --- | --- |
| `tests/unit/test_source_contract_reader_port.py` | `90586fdb5451e094efa6e52d72f9fe1187d4aac84151acd20f0639f66b567278` |
| `tests/unit/test_shared_reading_cache_precheck.py` | `3f593fae9ef2a9f291d7e02c80370a50462eac341a08978d31297a161ee52309` |

只读核对的相关产品 owner 字节：`source_contract/source_version.py` 为 `2bbdb09579cb68bae4e4a7de94998e6317137f463e9e4f6868b66d247fbf488c`；`automation/narrative_generation.py` 为 `f74c9af32c239bebbf867cc1e41618a11ca24092d3c80b7a761965bf519578d3`。本 agent 未修改两者；其他作者仍可按分权推进不相交工作。

下一步仅交 ROOT 对这两个测试变更做独审、统一提交和候选 CI；本 agent **STOP**，不自行并线或继续扩大整改范围。
