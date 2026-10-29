# W20-FF第3轮ROOT复验（2026-10-29）

**原两项实质返工已通过；发现一处三态字段迁移遗漏，由ROOT隔离修复，暂待最终复审，不再发作者第四轮。** 作者HEAD `2b610881b9da509d6fb3f3bcbeb5b32707e051f2`；实现`48362b7`（aa49836仅清理文档），后续实现无变化；26条交接SHA匹配。192短测通过/6.25秒，两个真实报告完整新版oracle复核0findings。

## 已关闭

- 同次新增采集丢回复：真实lostreply样本dd7884e1首次1GET，harness输出边界消费成功envelope仅供证据并标截留，公开query+reader实读相同Ref/SHA后首次恢复0GET/同Ref，再次0GET。此为明确的传输层丢回复仿真，不声称真实外网断包或精确commit微秒杀树；服务端已完成允许。旧prior-delivery空kill只是CONTROL ONLY。
- 探针并发：父全局stdin/stdout/last_error已移除，一调用一受界子进程，三态独立。ROOT并发边界反例A/B各自payload/ref不串、父stdio未变；非零child→probe_error。最新真实读回路径确认成功。

## 唯一剩余 FF-R3-1 [P2] 三态字段迁移遗漏

`w20_case_specs.py:373`仍读旧`durable_at_kill_public_readback` bool；当前`case_call_kill_after_import`已输出`durable_state_public_readback` string。实际handler接正常not_found仍FAIL（两条缺bool诊断）。这是本次probe API迁移的一处漏接，不是新产品权限门或原件问题。

ROOT在独立filing-fetch-w20-root-final修唯一owner：只有not_found能做pre-durable负证；confirmed/probe_error/missing/unknown都不能。旧历史bool报告保留历史，不改为当前PASS。新增当前handler契约TDD后，定点复核即可，无需全41/404秒全仓或再转用户。

## 小证据、测试与清理

[evidence/ff/README.md](evidence/ff/README.md)含可移交反例、精确旧case和最新真链case/原report SHA，约小JSON而无SDK/原件/整attempt树。当前192项范围、命令及真实耗时见同名JSON。作者冻结视图已按卡删除，因此未重跑依赖本机隐式site-packages的真实catalog单元；用公开reader真实既有报告+独立边界反例验证，未冒签新E2E。

ROOT pytest目录已删除恢复不存在；作者worktree clean、索引/source只读，0新外网/收费/下载/安装/merge。非阻塞计数文书不阻并线。等待ROOT新源码后仅复审此漏接，再给最终PASS。
