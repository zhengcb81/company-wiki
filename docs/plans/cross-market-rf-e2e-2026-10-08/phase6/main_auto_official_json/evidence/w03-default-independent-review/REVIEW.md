# W03 默认策略修复：集中独立复核

日期：2026-10-11。当前结论：**一个精确语义 blocker；其余已检查责任接受。**

## 范围和真实证据

只读当前隔离 MAIN 的 policy/groups 两生产文件、追加的 14 个参数化案例、五项旧失败断言、ROOT 的两份职责测试及 W03/W04 原卡。没有源码、测试、配置、原件、共享 PWF、安装或 Git 写操作；没有下载或供应商/模型调用。只执行两条完全内存的原生 selector 反例/正控，没有重复全套、预推送、122 节点或公共大节点。

已核 owner HANDOFF 实际 SHA：`9e6647b5fd698c5e6fcbfb883da5034c9bdd5abadde3c3dec594ced2326f559e`。owner final-sha-index 中所有证据 SHA 匹配。原正常推送日志与 owner 保留副本字节相同，真实结果 **7 FAIL / 3137 PASS / 197.27s**；推送被既有 pre-push 阻止。原字节 SHA 为 `389f0e29b686f15b3ba861838fc1a92cd9068bba01b301e6e3723c43a87e18c2`。原日志含非 UTF-8 片段，本审只以 replacement decoding 看文字，SHA 始终计算原字节，未重编码原证据。

owner 集中节点实际 **122 PASS / 35.96s pytest / 38.4066744s 外围**，包含全部当前 evidence 60 案例、business recall 56 单元、4 集成和 2 指定公共案例；**不是**重新跑完整 public3。ROOT 两职责测试实际 **20 PASS / 2.71s pytest / 5.2327685s 外围**，Ruff 正常。精确命令、原生日志 SHA、运行前后保护及清理有现存 receipt，均已核对。临时目录确实不存在。

## 已接受责任

1. 现实际 diff 只有两个通用生产 policy/groups 文件；五项旧断言均保留，只在 evidence 测试末尾新增案例。修复不按公司名、代码或文件名单放行。
2. 真正具体的产品用途、控制器/执行器构成、按订单生产/模块化流程、经销商安装关系仍可被选。旧静态类别、管理套话和目录噪音负控保留；行业出口许可变化由原纯业务与公共 CLI 的真实内容测试保护。
3. 已选中的产品先行段落与紧邻、明确指代的真实事件加入同一个既有原子组。明确限 1 时双方均省略且标 partial；限 2 保留两个原文 locator，不仅留下后半个肯定事件。不改原理由或提高排序分数。
4. 新桥限同页、连续 paragraph、PDF text、相同 source/parser/version/role/language，且 speaker/QA/parent SHA/projection/record/section 一致；排除财务/目录/未知主体、native JSON/其他 OCR 的错误拼接。已有多成员项目/PDF 组不会被替换，既有单成员标识可合法扩展。四个新边界案例改为“不得共享组”，而非“每个单元都必须没有任何组”，后者确为错误的新测试假设；旧五断言没有因此更改。
5. 显式 0.6 走旧算法，pure dispatcher 文件仍 SHA `64b724df8b879b6859832facd4d18cf7f306b927611439f037c554c6e557e616`。真实 MSFT TXT 不变，旧 ordered fingerprint `11ad9c7f21c92d10847861f387a16ce1035f94da6a47a50128b354d0594b6d9f`；本修复后新 0.7 完整指纹仍为 `c5e498acbb5d5c158a030b6e4d3bcec3713f408f2c49baa85717b3d63b905478`。新 103 候选/96 选中/7 省略、partial 是真实限额状态。新公共默认测试及真实 locator/9 锚点没有改断言或伪 retag。
6. ROOT parser 边界测试显式指定 0.6，有注释说明历史 parser replay 与新政策 cap 分离；另外的真实 current 0.7 公共测试仍保持。故这是一项职责隔离，不是将现新策略负控全部钉到旧算法绕过。
7. W04 失败响应正确记录观测的 **decoded final** SHA，原始 HTTP JSON wire SHA 是独立诊断。ROOT 截断测试使用实际返回 final/wire 计算，确认两 SHA 不同、UTF-8 长度/完整未裁剪 prefix，失败 accepted output_bytes=0、output_sha=None、settled_at 已落，重入不再请求或再次收费。现 caller `narrative_model_caller.py:243–244` 明确 final_content_sha256 且 no_output=True；HTTP 模型 `narrative_http_model.py:450–459` 用原 wire 与观测 final 构造失败诊断。没有将“失败”误解为“从未观察到响应”。W04 源码未改变。

## 唯一 blocker：列举助词被当成具体业务组件

最小原始反例（纯 in-memory native selector，title=招股说明书.pdf，显式 0.7）：

> 公司产品包括各类设备及配套服务等。

期望：仅通用类别，不含具体产品/客户/用途/流程关系，应不选。
实际：selected，selection reasons 为 business_narrative_signal + business_structure。

同次具体正控：

> 公司的产品包括工业控制器与电动执行器。

期望和实际：均 selected，保留具体组件信息。

根因定位：`narrative_business_policy.py:49–64` 新 component list 捕获“各类设备及配套服务等”，分割为“各类设备”“配套服务等”；第二项仅因普通列举尾词“等”不被 generic-component.fullmatch 接受，便被推为“具体”。这与标题/公司/存储/身份无关，是通用列表识别缺口。不能靠名单或改变已有断言处理。

建议原 owner 在独占 policy 源范围处理**实际列表语法中的列举助词**，用原文不变的分类 token，而非改写原件/locator；先新增此负控，并保留具体组件/用途正控。单独定点验证此根因和已有 14 案例足够，不需再跑 122/public3/whole suite；更广真实语义研究仍属于 W09，不能宣称有限启发式已语义穷尽。

本轮已将精确反例交 ROOT。**在该负控修复前，不宣称整体默认语义验收 PASS。**

## 保护、恢复与冻结

`receipt.json` 保存本轮开始/结束的 13 个精确 source/test/TXT/config SHA，全部相同；未扫描全 261 源，避免与并行 W08 独占写集混淆。正文无秘密、无新身份/许可/签收门。当前自有 probe 不创建 TEMP/数据库/HTTP 服务，因此无清理残留；owner 与 ROOT 的既有 TEMP 清理凭据及真实目录状态均核实。只在本 evidence 子目录写入本报告、最小 probe 与 receipt；原 RED/owner evidence 无写入。

该报告在现 owner stable SHA 下冻结；未来修复是新源码快照，必须单独定点复核，不能修改本轮历史反例。
