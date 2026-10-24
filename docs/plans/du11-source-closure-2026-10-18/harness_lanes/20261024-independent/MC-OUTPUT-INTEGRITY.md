# MC-OUTPUT-INTEGRITY：会议转写输出的完整性与安全写入

状态：READY；与最近已完成的 MeetingConverter CI fast-gate 卡独立。项目 C:/Users/郑曾波/Projects/MeetingConverter。独立工作目录 C:/Users/郑曾波/Projects/MeetingConverter-output-integrity。branch codex/meetingconverter-output-integrity-20261024。冻结起点 master@8a33a7f96292af8e6574d98b959703c6d11919eb，origin/master。派卡时原工作区有既存修改 M .coverage；必须保留在原仓，不能复制、暂存、覆盖或删除。

## 根因与目标

core/output.py 的译文和双语 writer 用 zip(paragraphs, translations)，长度不等时会静默丢掉多出的尾段。三个 writer 都直接以覆盖模式打开最终路径，格式化或写盘中途失败会截断旧结果、留下半份文件。修正输出边界，不改识别、ASR、批处理或翻译策略。

## 唯一写入范围

允许改：core/output.py、tests/test_output.py，以及本卡 docs/plans/meetingconverter-output-integrity-2026-10-24/** 和 docs/handoff/MC-OUTPUT-2026-10-24/**。

禁止改：.github/workflows/**、任何 CI/pre-commit/push gate、core/pipeline.py、core/batch.py、engines/**、translator.py、配置/公司清单、真实 output/**、音频、API 凭证及其他仓库。

## 实施与验收

先用合成 Paragraph 和临时路径写反例。译文与原段落数量少一或多一时，必须在碰最终文件之前显式失败并报告 expected/actual；成功行为继续覆盖目标。对最终文件先同目录完整写入临时文件，成功 flush/close 后再替换；任一错误删除临时件并保留旧文件字节。不要建多文件事务框架；三文件不能整体原子提交的边界要写清楚。

测试三个 writer 的成功输出、段落逐条和 UTF-8 中文/英文、时间戳开关、空/单/多段、长度不足和过量、格式化中途异常、临时写入失败、目标已存在时失败保留原 SHA、成功重跑覆盖完整文件、无孤儿临时文件。输入和输出都只在 pytest tmp_path；记录开始/结束清单与 hash。禁用 MiMo/DeepSeek、网络和真实音频。

运行：

    python -B -m pytest -q -o addopts="" tests/test_output.py
    python -B -m ruff check core/output.py tests/test_output.py

确认不修改 workflow。不要以聚焦输出测试冒充全仓 coverage 80% 门或远端 CI 通过；分别记录精确范围。

## 独立审查与交接

提交任务分支后，未参与实现的独立 agent 审查完整 diff，特别挑战 zip 静默截断、Windows 替换语义、失败清理和旧目标字节保留；自行运行本卡测试并加入一个写盘失败反例。修复所有发现、重跑测试并对最终 SHA 复审 PASS 后才可交接。交付 docs/plans/meetingconverter-output-integrity-2026-10-24、docs/handoff/MC-OUTPUT-2026-10-24/handoff.md/json、review、日志及临时目录恢复证据。handoff 明确说明原仓 .coverage 保持原状且未进提交。
