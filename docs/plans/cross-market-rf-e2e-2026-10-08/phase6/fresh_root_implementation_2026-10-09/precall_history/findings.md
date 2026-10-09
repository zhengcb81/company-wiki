# W11 Findings

现有audit_run.capture只启动command、记录UTC/argv与有界输出；argv中的draft路径可在后续步骤覆写，历史日志虽完整但不能复现当时输入。RF本身validate-only零写语义不应改变。修复责任在显式外层记录工具及executor约定，不是给每个RF入口加许可证或事后重建等效JSON。

主仓CodeGraph索引存在；audit新工程没有索引，已知精确audit_run路径直接读文件。本次没有新增索引、网络/收费、生产原件/配置修改。audit同步工具保留未知文件、只增加/替换本技能文件，但尚无selected-file选项；实施时需先算实际包差集，定点写接受文件，不能顺带同步其他状态。

RC23同时含人工document_matrix旧request_id和TRUST_BOUNDARY.md缺件。先检查RF现有compliance/session contract/renderer是否已提供真实状态生成函数；复用当前机制。声明必须来自实际unsigned/hash/evidence状态，不能新增签名、签收、审计许可证。新索引只引用实际保留的request/call/result，未解决资料保留gap。验证只是交付完整性，不证明研究质量。

2026-10-09独立major审查：既有11测试绿仍有真实P1输入/输出同路径覆盖历史，以及P2声明清理错误遮蔽主故障，暂未验收。新增4控验真实1FAIL/3ERROR→15focused PASS/2.263s。实现显式argv位置/歧义不启动、原字节历史与执行副本隔离、公共atomic writer保留主故障、post-call有限输入完整性且child真实exit保留。旧重复读入正例用明确实际input indices，未降断言。第一次写测试仅CRLF marker定位失败，故原日志重命名prior_tests_only，不冒称RED；真正review_residual_red保留。下一步完整suite、新版本native联调和独立复审，一次大节点通过后commit/install；零外部费用。

2026-10-09集中独立复审通过工程范围：sourceSHA2c30b29fe64c78deef194ace0650ad73d3402e22510995baa2cf184c5ae54c57，15focused/2.199s与10独立controls（合法/非法输入index、input-output歧义、2×物理cap、childexit9与timeout124主因、两atomic双故障）均绿。TEMP基线恢复/absent、零外API/付费/M3；旧独立FAIL保留。非阻断文案统一consumed_path，源码无变。MAIN接受M2，可正常commit及四文件定点同步；RC23 document_matrix索引及原三家研究仍需M3新attempt实际验收。

W11已正常commit9b10767（canonical无remote，未创建远端），四运行文件定点安装到两个独立物理根.agents/.claude，共8文件/132566B；baseline既有内容与1a22dfd一致、逐项旧SHA/CAS/原子替换；unselected code/reference drift0，两个实际installed CLI新接口probe绿、配置/output/unknown不变。GBK默认编码调用quick_validate曾失败（工具read_text环境），显式python -X utf8原工具Skill is valid，未改skill-creator系统文件或降低校验。新版59全suite/15focused/4native/10独立controls与历史FAIL均保留；M2完成，M3新公司与document_matrix实际索引仍待。
