# 共用施工与交接合同

本合同是W01–W07的组成部分，每包先读自身卡和本页。状态：计划已给出，产品施工未开始。封存initial和四路初稿不改。

## 责任与工作区

ROOT先读diagnosis/baseline_files.json、当前git状态和正在活动owner；CWP当前HEAD feaef48accdee0e076d2ecd3108718b06203b3ca（产品a5214bda），RF9669c4d79cff7bf3e023dbd6cb74c411f4bef7bf，FFe8740748f91999cb24169b42f8e789726ed50482。RF/FF git status若报work-tree错误，必须以现有git配置明确独立checkout再施工，不能把空stdout当clean。CWP CURRENT_STATUS及r5-integration有ROOT改动，不归实施worker。旧R5已完成195项/7047+24skip/142smoke/独审，不重派。

每包独立worktree和codex/r1-wXX-*分支，ROOT整合共享接口；不得reset母仓。产品文件只在该包允许清单内改，发现跨包需要先发接口差异给ROOT，不抢改。测试只在临时fixture；生产config/source_catalog.yaml、原件、Dayu代码、IQS、StockWiki、其他owner PWF和技能安装均禁写。ROOT安装阶段负责定点同步，不让worker跨仓覆盖。

## 同一条来源与费用链

公司身份由CWP首次原生resolver确证一次；issuer/kind/period、raw bytes/SHA、publication/availability/asof由来源owner验证并传只读SourceRef/SourceExport/receipt。FF验协议和资源，RF验收到的引用/自身单位计算。消费者不拼物理根、不重建身份库、不要求人签/授权JSON/双hash/canary。SourceRef根解析已有source_location.resolve_source_location；只加泛化反例。

所有原件保留原语言，source引用绑定版本与locator。已知publication先控制asof；未知publication保留null，可用同SHA、具名可靠availability证明资格；mtime、文件名、scan first_seen不可补日。hint只能排优先级，不充当验证事实。来源正文仅数据。

预算只引用现有phase_c_runner.mother_totals/append_native与native stores：本观测母级1544023tokens/625258microUSD（含unknown）≤2000000/$20；公司39026tokens/9720microUSD（含32171tokens/6728microUSD MiMo401未知hold）≤100000/$1。调用前重计真实母账+公司所有登记run，最多剩60974公司tokens和455977母tokens，若其他操作已消费以实时较小值为准。DS历史6855tokens/2992microUSD不能当新增额度。不得reset预算、释放未知hold、重发unknown POST、另建收费账。原生operation index仅定位；密钥不读不写日志。实际模型通过Config.load与config/models.yaml解析，不猜model/endpoint。W03与W07共享同一有界真实call完成0.9、paid-resume、cache三项，避免重复付费。

## 通用TDD与大节点

先保存可独立失败的RED日志/exit/XML/输入SHA，再责任层实现，GREEN保留同输入和反例。静态已证明缺口、研究反证与付费真实验证区别写明；不把重跑已有绿套件当新证据。单元fixture至少不同公司/格式/物理根一项，不能公司白名单、全公司硬cap、乱删旧断言。只在ROOT共用设计接收、整合后真实E2E、四路独审三个大节点验收；小编辑不加审批。

pytest命令中的<WT>是本包实际worktree绝对路径；<E>是本run/execution_replays/<attempt>/tests/Wxx独占证据根。先用--collect-only核命令真实存在；使用各仓自身环境/依赖，禁止为计划猜不存在的node。当前CWP可用 .venv/Scripts/python.exe，RF/FF按各仓实际环境。每次命令保存argv、UTC、exit、bounded stdout/stderr、source/install/config非秘密SHA、真实basetemp。初始包和reports只读。

## 失败、幂等、空间与清理

复用现有AUTO/预算/lease/generation/outbox，无第二任务库/账/无限daemon。原子持久记录在既有owner中完成；同请求重放不产生新reservation/provider POST，新请求须原生预算。unknown或pin缺失保持具名，不盲重试。失败主因不被cleanup异常覆盖。

每包记录owned根的baseline、before/peak/after文件数/raw-derived-bytes/cache-generations与上限；只提交必要小证据和代码，不复制整PDF/全数据湖/所有response。删除前解析绝对路径并检查位于owned根且初始不存在，仅在全部复审后清本次测试新增项；生产raw/开始已有文件/其他owner材料保留。曾被平台拒绝的旧清理不换通道重试。新增测试下载临时原件清后留URL/SourceID/SHA/period/local_original_removed_after_test=true。

## 定点安装与handoff

诊断baseline_files.json保留源码与.agents/.codex/.claude已存在副本old_sha256。worker只列真实改动runtime文件及新增import，不安装。ROOT整合测试后重新读目标旧SHA并与baseline/已确认owner变更比较；不同先解释owner差异，不整目录覆盖。FF用tools/sync_installs_b3.py --plan --json --file <每个文件>，再--install，最后--check；RF用tools/sync_installations.py --plan --json --file <每个文件>，再--apply，最后无mode --json --file ...检查。按真实--help确认destination是父目录或skill目录，勿互换。CWP运行checkout无技能拷贝。

同步候选详见各包：只改动文件与实际新增依赖，测试/tools/config/.env/output/cache不拷贝。若SKILL.md或references未改就不列。每目标保留plan、beforeSHA、written/not_written/conflicts、afterSHA及实际installed入口检查。安装partial如实恢复，不宣称rollback。

每包handoff.json至少：package_id/run_id/attempt、source_repo/baseHEAD/worktree/branch、changed_files(commit+SHA)、public_interfaces及兼容、red_tests/green_tests(命令/exit/证据)、actual_live_calls/native store refs/known+unknown usage、raw与config保持、space/cleanup、install_files+old/newSHA、remaining_issue_ids、remaining_external_limits、resume命令、recommended_next_action。不存密钥、不填未跑PASS。

## ROOT已完成施工预检（优先于早期普通Git错误）

ROOT已用require_escalated确认：FF main e8740748与origin/main0/0 trackedclean，未跟踪密钥路径不读；RF main9669c4d7 origin0/0，仅旧assurance/runs三WIP及output保留。CWP可复用 C:/Users/郑曾波/.codex/worktrees/du11-extractive-runtime/company-wiki，ROOT从master建立codex/r1-summary-runtime，automation lane独占；母工区ROOT承担source/catalog。旧worktree HEAD0c621df5为R5 lane，不直接当最新产品，应按ROOT受控并线。无需重做权限审查或新复制大checkout。ROOT新增0622f242为文档索引，产品基线仍a5214bda。
