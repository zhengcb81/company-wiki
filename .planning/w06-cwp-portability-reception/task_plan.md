# ROOT W06-CWP-PORTABILITY 接收计划

状态：工程与独立验收通过，已正常并入本地主线；远端发布待记录。仅合成 Windows 存储/Reader/CLI 及工具判定范围。

- [x] A：原交付范围、22产品及6输入核对；原始失败封存 intake/。
- [x] B：目录归属、最小子进程环境、完整 SourceRef 实读、真实 CLI 输出、typed oracle 共因修复。69PASS/1宿主symlink SKIP/9.07s，七场景4.051s。
- [x] C本地：非作者53案例全部符合预期，原4错误输入SHA不变且正确FAIL；ROOT接收5f10af0b，正常merge master e2e19ea2。
- [ ] C发布：提交接收证据与PWF，正常push，记录精确远端HEAD及对应CI；清理ROOT干净工作树，保留branch/worker/evidence。

证据位于母W06/evidence/root-cwp-portability-acceptance/。最终产品freeze见 fix/verdict-aggregation/product-freeze.json，独审见 independent-verdict-final/report.json，本地主线见 local-main-integration.json，发布后见 publication.json。

这是显式手动工程工具，不复制到技能、不自动每commit跑七场景。原FAIL及原件保持；本包零provider/LLM/费用。生产许可和配置没有新增。母W04/G2/G4/G5仍开放。
