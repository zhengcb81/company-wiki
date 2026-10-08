# CN-688012 v3 修复交接

状态：**PARTIAL，正式预测已完成，等待原独立审查者复查 CN01–04 变更闭包**。

## 修复范围

- CN01：把全部残差称为售后的错误解释取消。正式分段改为 NonEquipmentResidual，1857.63826811m 只是集团总收入减去四舍五入的专用设备收入。九个未来金额仍为分析者假设；年度48/53/65及半年19/23真实业务上下文已绑定，收入确认政策只支持会计时点。没有编造设备存量、续约率或量价机制。
- CN02：客户A 39.99%/22.15%来自年报219完整原文，绑定九个未来验收腔假设；SEMI2027/28 21.8%/14.1%与中国2026增长放缓分别绑定。TSV先进封装原文补齐。四个风险节点各用真实适用风险，不再把半年33泛指客户资本开支或全部交期。
- CN03：全部19条公告分别写明重要性和原文是否打开。通过现有SID工具实际获取9份全文，八份公司公告、一份保荐人意见；并不冒充FF→CWP入库。资金/借款/资本开支不等同营业收入。1225482911公司正文确认总部研发完整投用延到2027年12月，九个验收腔假设及设备反证明确采用该约束背景。1225482894新发现达产后属地销售300000万元计划，因年期、年度/累计和集团外部收入边界不明登记为capacity_plan+ambiguous+mismatch+unmodeled_data_gap，未硬加收入。1225482917关联销售预计额度是交易授权，客户2/3是董事任职的外部关联法人，并不默认集团内收入抵销。1225482880提到激励计划收入增长考核，数字/期间原激励表未取得，明确保留缺口。
- CN04：用独立审查者真实重取同SHA的8月20日官方PDF收据，调用标准append-only source-facts改transport source_url。随后真实RF→FF→CWP再复用：日期8/20、URL8/20、原件SHA相同、零下载，新capture进入v3。没有直接写数据库、改原raw/旧sidecar/旧acquisition receipt。

## 正式检验

最终lint、hashcheck、validate-only、engine/Markdown、强input-required验证、逐条106个claim原文匹配、9行独立公式/增长率/CAGR/增量、非交叉/H1下限、immutable snapshot与registry audit全绿。新文件均在独立TEMP/CN-688012/v3。原v2 input/forecast/md/snapshot_v2与原manifest全部SHA及字节数不变。原命令日志继续追加，旧manifest封存时的日志前缀不被重写；不要把新增日志误算旧主产物变动。

## 真实未完成项

CWP Worker没有运行（仍BLOCKED/not_run），孤立PDF解析不算canonical narrative处理；IR原DOCX/投资者PPT、A股电话会TXT未取得。未拆分残差的数量校准未知。二期销售计划年期/口径不明。股权激励增长考核原schedule未取得。模型绿色不能把上述项改成端到端PASS。未来实际业绩未知，backtest evaluate不适用；真实签名状态仍unattested。

## 审查入口

先读repair_v3.json与manifest_v3.json，再查fact_checks_v3.json、announcement_triage_v3.json、formal_verification_v3.json及commands实际收据；只复查本次变更及其依赖闭包，保留v2独立原审查。正式研究文件在manifest_v3指向的TEMP路径；共享PWF/其他公司目录/Dayu保持。
