# W08 main 发布前独立补审

**有限补审 PASS：17P/0F。** 母仓main的同13原oracle路径适配复审13P，加原prepush四个旧边界4P。27个母仓实际绑定文件前后SHA一致，实际src/tests导入路径已验证。未复跑8k/2132、未重解析PDF或调用模型。

绑定：main基线`e09e44e1`加冻结改动；`C:\Users\郑曾波\Projects\company-wiki\.planning\r1-w08-prepush-final-rootfix-20261024\main-actual-freeze.json` SHA256 `8f698f3e5ebbb875e73933ee02f358bdc53554f5e04bfadea406a86b029dbcda`。这是实际工作树字节审查，不是对尚未运行的普通prepush、push或CI签绿。

两项根修符合原合同：大小写与plural保持，共用既有Latin头词边界，完整长名称不再产生四个假Product；正证家具继续接受旧native header/footer，保留source/frame/font/lane/coverage/order及footnote/table拒绝，不添加list24或新身份门槛。

路径适配准确记录两处harness-only差异：WORKTREE改为母仓；main setup以setdefault优先freeze中的实际raw SHA，避免旧LF常量覆盖母仓CRLF字节。原脚本保留；全部13case函数、产品调用及40个assertion AST不变，main setup AST确有变化。实际脚本SHA `44db4fcf271af51292867a4f65b4575f914ba58aeeb139c2098450dc54204d1b`，证据为main-path-and-freeze-adaptation.json；不能称整份脚本字节相同。

原四函数AST与补审前baseline一致；两个long-Latin声明、正证header/footer句子续接、页内paragraph重编号全部实际通过。执行见independent-execution-main-final.json及original-four-execution.json。cache反控仅进程内scoped read_bytes，无真实源码改写。

原V2 12P/1F、V3 13P及其报告保留各自版本；普通prepush原4F/8052P/24skip日志保留，不能改称已通过。ROOT后续按现有普通prepush完整运行；本次未绕过门禁。年报14仍是V2部分诊断，本补审不签全内容、收费摘要或RF环节。

cleanup-main-supplement.json记录0 Temp根、0 source/test/Git写入、0网络/模型/PDF/备份及实际SHA守恒。不宣称其他任务或全仓临时目录全部清空。
