# MAIN：OCR 与有限 Worker / 公共 read 的统一接线

状态：待 parser 包交付后实施；不改变两个 parser/generation owner 的独占文件。单一大节点先责任 RED，再真实 22 页 batch / public read / 默认复用。

## 调查后的接口决定

- 纯 package parser 不读取部署配置。新增薄 normalization composition，负责从当前 project root 的 `config/local_ocr.json` 读取明确配置，缺文件沿用纯解析。配置格式直接使用已交付 `LocalOCRConfig.from_dict`；非秘密资源路径仅在存储/进程组合层，generation 的身份只含 SHA 和实际处理参数。
- 每个 worker 进程拥有自己的 adapter/ONNX；配置在 batch 开始读取一次，非秘密配置快照传给 bounded child，不能在处理途中静默改模型。公共 read 使用当前显式配置，遇旧 fingerprint 不匹配具名失败；保留配置即可重放，不自动安装/下载/fallback。
- HTML 仍 parser 1.0.0；纯 PPTX 当前 1.1.0；OCR PPTX 2.0.0。旧 1.0 PPTX locator 按原内部 slide_id 回放，新 locator 按 display ordinal；不把两者混用。PDF/TXT 不因 OCR 配置变化失效。
- 将 pathless normalization identity 接入跨 run generation_manifest 的 parser_components；未完成 run 的原生成身份不重新签。已完成旧 artifact 可以按其旧版本实读回放，不用当前 parser constant 否决旧 locator。
- 当前 generation.read_reuse_pin 把 `selection.coverage_complete` 作复用前提。这对OCR会把已完成、每条已精确回放的精选摘要永远当miss。接线时必须 TDD 区分“精选派生产物完整”与“全文召回完整”：completed summary + 可靠选中span可以复用partial来源；successful skip仍需全文coverage complete且没有span。损坏/未完成/不可靠selected span不能复用。

## 实施责任顺序

1. 对配置加载/无配置纯解析、路径搬移同SHA、坏SHA/版本/阈值、parser dispatch 写 RED。配置只控制处理方式，不是人工授权门。
2. `narrative_formats` 改 per-format identity；`narrative_runtime/worker_factory` 注入同一 normalization port；`narrative_select/verify/replay/transport` 使用 port，不各自读取模型或拼模型路径。
3. language 检测复用现脚本计数法；本机全图 PPTX 仅取有限真实图文样本，不按公司/市场猜语言，也不为了判语言再识读全22页。初次 select 才读全部所需图；选中 span verify/read 仅识读 locator 指定的 unique media，每图一次。不落完整OCR文本缓存。
4. 区分 source coverage 和 selected-span correctness。选择中有高置信、可精确重放的经营文字时可以输出 partial；未识读/低置信/错误/空白与图表关系不可靠仍留质量诊断。无可信 selected span 的 opaque 来源保持具名 incomplete，不能成功 skip。选中低置信或损坏 locator 不进入 verified。
5. 保留现有 selection.coverage_complete / partial、EvidenceSpan flags 和版次绑定。只有实际交接显示这些字段无法保留必要小型质量诊断时才添加明确 optional quality 字段；不为了接线另建质量/权限数据库。
6. 保留 Worker 外层硬 deadline、bounded profile、scratch/persistent guard 和预算账。Python ONNX 前后检查只是协作限额；测试硬中断不留下可见成功物。
7. 真配置只使用本机已经验证的 RapidOCR3.8.1/ORT1.26.0/三ONNX的实际SHA，正式上线前读取当前资源再次核对。其他安装缺资源要诚实说明，不能称已具备。

## 集中验收与交付

- 旧 PDF/TXT/HTML 公共契约和格式测试；旧 PPTX 1.0 回放、新 display ordinal、OCR 配置指纹、fake adapter 确定性选中及伪造拒绝、多 span 一次回放。
- 真实原22页 deck：先通过 official local import 返回真实manifest SourceRef（已由MAIN补PPTX并28项GREEN），正常 normalize 与至少两页密集原图对照；0网络/模型下载。
- parser owner真实结果：22media/1067lines，初次145.549秒；8span只回放4media16.570秒。页7分部变更首句/页18副标题漏识、双栏顺序不等于tablecell，因此coverage=false保持。首次真实batch总deadline须根据实际耗时配置（包括select、model及selected replay），不能沿旧40秒夹具值；测试固定失败不改语义断言。
- 同一实际 public finite batch → bounded worker → bundle → reference/read：原语言、partial全篇质量诚实、精选业务证据精确。只对小型selected snippets调用当前配置的文本LLM及累计预算，不增vision provider。
- 第二run默认复用返回同exact pin，0模型POST/新费用；显式refresh和模型/阈值改变仍遵守生成身份。不以缓存命中绕过实际原件SHA/选中locator验证。
- test根/临时图片/模型小文件恢复初始状态；原件和其他owner内容零改变。记录main精确SHA、真实结果、限制、收费/unknown和清理。

后续依然按 `fresh_research_major_node.md` 做原三家及新三家公司真实执行/四独立审查，工程OCR与算术通过不代替研究验收。
