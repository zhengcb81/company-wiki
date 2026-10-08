# R6三包主线查收

状态：分包责任验收通过，进入主线并线与接线。不是产品全流程验收。

|包|真实交付HEAD|本轮集中复验|遗留主线事项|
|---|---|---|---|
|R6-FORMAT|d48ca1be9d377e14e3926b2c0ec1872ff08e0667|64PASS/12.45秒|Worker路由、表格选择、原语言、版本及一次批量locator回放；真实22页全图PPTX无文本，仍partial|
|R6-RF-INPUT|b1763fc034558674b56c941e0b13620df9c11a12|204PASS+8subtests/12.60秒|真实NarrativeRef消费、新研究、安装闭包；handoff宽集99FAIL/4ERROR不可记成绿|
|R6-FF-CAUSE|8bb7b85f57ca7effed2a42afe8fbcdbba72c15ff|36PASS/4.29秒|CWP机器原因/实际provider_started与usage证明；RF消费诊断；当前unknown不猜|

## 交接核对与并线方法

三包功能文件清单SHA全部匹配，写范围无交叉；FORMAT与RF的handoff.head指功能提交，后续HEAD仅提交交接清单，差异已解释。FF未提交仅HANDOFF.md和handoff.json，先定点提交这两项，再并入main。RF既有assurance/runs和output、FF密钥配置属于主目录原有文件，保留，不加入本次提交。Dayu零写。

由MAIN合并各自已交付分支，保留原始功能提交；不重复签身份合同。主线只在集中接线节点跑相关集成及真实原件验收；最终两组新研究再做用户要求的独立质量审查。不得用合成E2E冒充真实网络、收费模型或图片识读。

## 简化约束

来源层负责公司/期间筛选；入库层负责字节和原子保存；读取层负责当前SourceRef原件；解析层负责定位可重放；RF负责数量/目标/证据语义。不让title、URL、语言声明、旧policy观察或人工receipt重复决定访问。新的解析批量回放必须一次解析并匹配全部选中locator，不允许每个span重新解析全文。
