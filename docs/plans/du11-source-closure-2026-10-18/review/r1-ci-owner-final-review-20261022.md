# R1 CI / output-owner 独立收尾审查

结论：**PASS_ENGINEERING_CONTENT_BOUND**。审查绑定 HEAD `20a7fb0cae4c3e1a56cb0cb7cb9adb9346b58deb` 与 JSON 内逐文件物理字节 SHA；不是对新远端 CI 结果签收。审查者没有修改产品、hook、测试策略或 PWF。

## 修复与发现

- `narrative_run_store.py` 原 `len != 1 or paid_response_json is None` 拆为两段，绑定局部 `paid_response_json` 再解析。`ReservationRecord` 是 frozen dataclass，短路、具名错误及非空解析输入保持不变。将新段逆替回旧段后，整文件 LF 规范化字节精确等于旧 `2f632193`；详细 SHA 见 JSON。
- **发现并已由 ROOT 修复一个 P1 共因**：只传修改文件且 `follow_imports=skip`，仍会漏掉此次跨模块 `Optional[str] → str`。隔离完整源码副本、真实 `pre_commit run`、固定旧 `2f632193/e51c…` 反控返回 0；不是仅凭 regex 推测。
- 同一个既有 hook 改为 `python -m mypy src`、`pass_filenames=false` 后，旧版稳定报 `narrative_run_store.py:1252 arg-type`，修复版通过。无新增行为测试、第二钩子或固定模块名单。
- CI 保留唯一相同全 src 命令；删除的固定名单步骤没有独有 strict 参数，删除属于去重。

## 实测与代价

| 检查 | 结果 |
|---|---|
| 原生 owner 独立反例、普通 paid 恢复及当时 policy | 10 PASS / 7.07 秒 |
| 最终 full-src hook / CI policy 断言 | 4 PASS / 0.46 秒；与上一组有重叠，不相加 |
| 隔离实际 full-src hook，旧版冷缓存 | 唯一目标类型错误，失败；42.574 秒 |
| 隔离实际 full-src hook，修复版后续缓存 | 通过；22.577 秒 |
| 原仓直接 mypy 热缓存（ROOT 观察） | 366 files 通过；9.106 秒 |
| silent 候选 | 14.561 秒后在 NumPy pyi 的 3.12 语法与项目 3.11 target 冲突处失败；不作可用替代 |

上述隔离 hook 时间含 pre_commit 开销；不能把原仓 9 秒宣传为冷运行保证。保留一份静态检查比维护失效的固定名单或引入依赖豁免更直接。

## 证据可靠性与边界

1. 首轮脚本读取了会移动的 HEAD，恰逢 ROOT 提交，两个 `original-error` 标签实际上是修复字节，**不计有效 RED**。最终反控显式固定旧提交，日志与 JSON 留证。
2. sandbox 首跑 4 PASS / 6 FAIL，失败发生在原生 artifact / paid-response 前置路径；同一有限选择 elevated 10 PASS。未凭此断言具体底层文件系统原因。一次 shell 引号错误也仅为审查脚本错误，已改用文件脚本。
3. 原 W01/W04 历史收据不改签。这次没有新公司研究、收费、网络、下载、生产原件或安装目录变更，也未增加身份/权限/人工签收门。
4. 原生临时夹具、隔离 Git 源码副本与 mypy/pre_commit 缓存已删除；仅保留短日志、XML、脚本和绑定收据。完整清理数量见 JSON。
5. `pyproject.toml` 旧注释仍称只检查契约模块，为非阻断文案残留；实际最终命令明确全 src。新远端 CI 由 ROOT 发布后另行观察。

详细绑定与命令：[机器收据](r1-ci-owner-final-review-20261022.json)。原始小型证据在同名目录。本线此窄审查完成。
