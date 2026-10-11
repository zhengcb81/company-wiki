# W05 拆分依据

- CWP 独立原件调查已证实：微软 PPTX slide7 的原始图片有两行业务定义；检测器找到25行，识别器两行输出乱码/低分，经0.5阈值过滤后只返回22行。定位在来源 OCR 层，不归咎 selector，不通过降低阈值把乱码当正文。更细的角度/recognizer内部原因未证实。独立报告 SHA `31a993a34a0b032933d2a189569a9f9625b9ab791db75e26a5fbc251a89f6204`。
- RF 真正 schema3.9 验证器只允许3/6/12完整月。G4 原生探针 `2026-05-31..2026-06-30` 被拒，半年度被接受。不能为通过模型把并表日期改成1月1日或把一个月当半年/全年。需要新版本的真实区间表达与消费检查。
- Audit 已有公司池循环的详细文字规则及P7诊断工具；第三卡的独立只读准备已STOP，证实8脚本缺进度reducer及恢复入口。不是已经发生丢样/重复收费的证明。report SHA `6024e21274548d43cb0912da33cea305e7b5cf80bd5ea1654939f0e38a7414e3`。
- 三新树原始物理工程文件分别16,477,278 / 3,894,822 / 417,782字节，合计20,789,882字节；没有公司原件/湖的副本。未来仅按卡片保留小型工程证据。
- 原件保全包已持久化158文件/11,683,687字节，71唯一raw，6个原生读者复验。它只覆盖有限清单，不构成删除整个旧TEMP的依据。OCR卡读持久原件引用。
- RF 最新 `1b616622` 已将15项财务日期反例接入既有快测，正常push299PASS/10subtests/29.43s；精确CI38123160491 success。原assurance/output WIP保留。

## 本轮工具异常与边界

Audit 的真实SKILL在 `skills/revenue-forecast-audit/SKILL.md`；先前猜测根SKILL不存在已纠正。不存在的 `references/review-protocol.json` 只读命令exit1，改读真实现有工具/文档，不生成假文件。CodeGraph索引未收录较新OCR/period_flow文件，读独立报告给定的具体文件，没有重扫/重建全仓。所有旧failed收据不改为PASS。

ROOT集成树新cards父目录首次apply_patch创建失败，未写两卡；改在已授权canonical工作区创建唯一发布路径，随后精确送入独立树，不绕平台拦截、不假称第一次成功。主计划文件的历史字节/EOL不重排。

## 卡片大节点审查

独立审查报告 [evidence/card-review.json](evidence/card-review.json) 保留第一次快照。两项发布前缺口已处理：三树固定input已落地；RF drivers.py精确schema族接线已纳入排他写集并加role-aware反例。RF基线不存在AGENTS，卡改为optional；重hash反例限定相对冻结输入；OCR明确composer整请求累计ROI资源。ROOT最终readiness收据核输入实际SHA/树起点/写集合，不把卡准备通过说成实现或研究通过。

发布前git diff --cached --check因两份新JSON的Windows CRLF报trailing whitespace，退出2；commit尚未启动。只将自己新生成的workspace/input-delivery两收据写为LF，JSON语义不变，不规范化历史PWF或封存审查报告。重新正常stage/check/commit，未绕过hooks。

推送本身exit0，随后read_text UTF8展示日志抛UnicodeDecodeError；保留raw日志SHA，解码时errors=replace仅供展示并核实际remote，未重发推送。该异常不是测试/发布失败。

## 分包复核 2026-10-11T08:49:32.889509+00:00

再次分包时使用现成W05三卡，不重复创建任务。OCR写document_normalization；RF写期间合同及consumer；Audit只新增pool-progress模块。ROOT继续selector/预算/配置和跨仓最终接线。三个独立目录已存在；docs/handoffs未跟踪项是预置输入，不应清理掉。
