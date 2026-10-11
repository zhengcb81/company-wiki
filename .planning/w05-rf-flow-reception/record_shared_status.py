"""Point shared PWF entry files to one concise, current reception summary."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'docs/plans/cross-market-rf-e2e-2026-10-08'
STATUS = BASE/'phase6/w06_parallel_verification_2026-10-11/ROOT-reception-status.md'
assert not STATUS.exists()
STATUS.write_text('''# ROOT 当前接收与下一步 — 2026-10-11

这是本批次共享 PWF 的当前入口。下面各计划旧状态是历史；失败证据保留，不重跑一次性封存脚本。

| 包 | 当前事实 | 后续动作 |
|---|---|---|
| W05-CWP-OCR | 已正常并 master8862372f、origin/master同SHA，CI38140484490成功。54集中+34非作者+148快测；正常push3257PASS。真实微软PPTX83.006s、原85/90s限额、22旧行保持、两条定义恢复。ROOT接受树已正常移除，worker与原件保留 | 完成；POSIX仅静态/未测峰值RSS，不认证全部OCR或研究质量 |
| W05-RF-FLOW | main/origin/main30ddae8e；CI38142227109成功。390+36工程绿、非作者31案例及16原P1入口均绿。17运行文件×2物理安装副本/34SHA匹配，未选文件元数据及assurance/output WIP保持 | 完成并线与发布；安装后小smoke留证，旧FAIL保留。仅数学与运行接口范围 |
| W06-AUDIT-MEASURES | main9cd5ff8a；296大节点/最终77/非作者反例绿，技能两份各26文件匹配。Audit无remote | 完成；算术审查不认证来源真值 |
| W06-CWP-PORTABILITY | 工具修复56PASS1SKIP，真实合成7场景4.755s，但最终非作者发现4类expectation_unmet仍汇总为PASS | 未接收并线；统一严重finding→verdict，再一次大节点复查，不修改producer |
| W06-FF-MATRIX | 环境/目录归属/typed oracle/绝对deadline及三市场fixture SHA碰撞已修，真实离线最终矩阵进行中。合法warm2024后缺期2025的实际响应有待ROOT共因定位 | 工具与产品失败分开；冻结→非作者验收，真实共因由ROOT改产品，不能以换fixture/skip换绿 |

## 执行顺序

1. 关闭 Portability 工具汇总缺口，接收 FF 矩阵的真实范围，正常 commit/并线/push。独立测试只有大节点，不增加人工许可或每 commit 全链。
2. ROOT 修 FF 矩阵实证的生产共因（若确认），重放原失败。
3. 返回母 W04：统一阶段谓词、重复信息与有用业务覆盖；旧selector指纹、原件SHA、硬cap保留。
4. G2真实有界摘要及RF消费 → G4原三公司执行/四路独审 → G5另三公司和指定公司循环。W04/G2/G4/G5仍开放，不能声称整个PWF完成。

本批次0真实provider/LLM/费用；原件、生产配置、Dayu、IQS及他人WIP不改。预算母账保持413778tokens/334463µUSD+FX2764hold，累计上限$20/200万tokens。目标工具当前active。

详细证据：W05/evidence/root-{cwp-ocr,rf-flow}-acceptance/publication.json；W06/evidence/root-audit-measures-acceptance/publication.json，以及另两包独立ROOT接收目录。精选本地计划 .planning/w05-{cwp-ocr,rf-flow}-reception、.planning/w06-{cwp-portability,ff-matrix}-reception。
''', encoding='utf-8')
groups = [BASE, ROOT/'docs/plans/narrative-evidence-pilot-2026-09-26',
          BASE/'phase6/w05_parallel_common_roots_2026-10-11',
          BASE/'phase6/w06_parallel_verification_2026-10-11']
for group in groups:
    relative = os.path.relpath(STATUS, group).replace('\\', '/')
    prefix = f'''## ROOT 当前入口 — 2026-10-11

当前状态、已发布SHA与下一步统一见 [ROOT接收状态]({relative})，优先于本文旧状态。
OCR/RF/Audit已并线发布；Portability最终独审发现汇总缺口待修；FF最终离线矩阵在跑。母W04/G2/G4/G5未完成。目标active，不增加小节点许可；原FAIL/原件/配置/WIP保留。

'''
    for name in ('task_plan.md', 'findings.md', 'progress.md'):
        path = group/name
        old = path.read_bytes()
        assert not old.startswith('## ROOT 当前入口 — 2026-10-11'.encode('utf-8'))
        newline = '\r\n' if b'\r\n' in old else '\n'
        path.write_bytes(prefix.replace('\n', newline).encode('utf-8') + old)
print('12 shared PWF entry files now refer to one current reception status')
