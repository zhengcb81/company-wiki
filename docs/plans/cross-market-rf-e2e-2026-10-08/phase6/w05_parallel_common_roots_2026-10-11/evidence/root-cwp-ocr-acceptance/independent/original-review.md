# W05-CWP-OCR 独立验收：原交付阶段

- 状态：**FAIL，等待 ROOT 隔离修复及冻结后复核**。不得将原交付直接签为 PASS。
- 审查对象：`C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr`，ROOT 固定 delivery HEAD `6fe9a82a6a96fe024774791e2018c882a098d512` / feat `4e3d28a9ba8a7df61c95860cc96b8088fe9f571d` / base `159b993e2f4d36c7e86dc12c9d6028f4a31b353a`。
- 实读固定 SHA：local_ocr.py `9b3b02a3891ac6c06bdb34f9244ca84c4cc73a67338b02bfcb1d1f9c120bc6f9`；ocr_composition.py `3b938a0fb2085713914f2593f7222d2318b26f2794515cf747dae67fc0979400`；ocr_region_recovery.py `c021cee73e2509bfa2c5e70a7a12d03aef6b2ca60b18ccccab578ab3368fae2c`。
- 独立反例：6 个，无导入/缺依赖假 RED；**5 FAIL / 1 PASS**。不重复 worker/ROOT 的全套与真实 OCR。
- 原始证据：`counterexamples.py`（8,098B，SHA `0ee1d69c4135fd49db47fe0ca7bac2c4782a3a5617b053555bdcfd60cc8d9169`）、`original-counterexamples.json`（10,646B，SHA `6c86ea1042bd1abded0fcbe6163e5842a22d6887fbaaa0ade06e1b8642fbda9c`）。原 FAIL 不覆盖。

## 必须修复的来源层问题

| ID | 级别 / 位置 | 真实行为与共用根因 | 修复和验收标准 |
|---|---|---|---|
| OCR-I01 | P1，ocr_composition.py:128/136；ocr_region_recovery.py:592/599 | 请求 cap=25,601，原图=25,600，只余 1 pixel；仍实际识别 290×54 ROI（15,660 pixels）之后才抛 `max_total_pixels`。累计仅统计并在回传后校验，不能在工作开始前执行总预算。 | 同一请求预算对象在每次原图/ROI inference 前预留像素，累计跨图，失败不得启动下一次。formal test 要断言调用次数/被阻止的工作量，而不只断言最终异常。 |
| OCR-I02 | P1，ocr_region_recovery.py:470/487/512 | margin 和 split-stack 各有实际 filtered-contract 反例：真实 adapter 已将低分剩余内容放入 `crop_result.region_diagnostics.dropped`；评估只看高分 `lines`，分别输出 `Revenue increased`、`Clean fragment Clean fragment` 并标 `recovered`，漏掉仍未读清的材料。现有 fake 测试把低分 OCRLine 留在 lines，未覆盖真实契约。 | 依据变换将 dropped 区域归回本 ROI/实际非微小 chunk；相关未读清剩余使整次恢复不完整，不能无告警拼成事实。外部 ROI 中的无关 dropped 不能误伤。原单位仍保留。formal test 同时覆盖 margin 和 stack 的 filtered 结构。 |
| OCR-I03 | P1，ocr_region_recovery.py:395 | split-stack 仅按检测框纵中心确定一个 chunk，却允许框跨两个拼接块/空白隔行。实际框 `(1,30,90,75)` 被伪映射到原图 `(92,9,181,54)`。这些拼接行来自不同横向原块，不是一个连续原图区域。 | 检测框必须完整落在一个有效 chunk 的 x/y 范围；跨块、间隙、pad 空白应拒绝或显式分解，不通过简单中心平移。未知/非法几何不猜测。 |
| OCR-I04 | P2，ocr_region_recovery.py:381 | 90° 回映射使用原 height 代 width；PIL CCW: 原 W40/H20 `(30,2,38,6)`→变换 `(2,2,6,10)`，实返 `(10,2,18,6)`。270° 对称项也须核对。当前 ladder 没有使用 rotation，但公开 helper 与矩阵宣称支持，现有 golden 镜像了错误公式。 | 明确 pre-rotation size + 角度约定，用非正方形图真实旋转的独立坐标期待验证 90/180/270；不修改正确期待来迁就错误代码。 |

## 审查通过或有意保守的行为

- 原正确 lines 只追加、不删除；旧 ImageOCRResult 三参数构造保留；低分原识别文本放诊断，不直接写 OCRUnit。
- 相同 media 请求内复用，算法身份键已进入 LocalOCRConfig 指纹。ROOT 修算法还应提升算法 revision，防止旧派生结果继续用旧指纹冒充。
- `detected=null`、`recall_status=unverified`、opaque 页保持：不能把 `recognized` 当完整召回。
- 独立 distinct-overlap 反例保留原单位并输出 unrecovered（PASS）。它可能保守地漏掉真实的新行，但没有假称完整；不能因此盲目放宽空间去重。
- worker 的两条真实定义 + 原22条逐字/box/score保留/replay结果是可信的局部工程证据；ROOT 仍需在新的冻结代码重跑。不是 W04 选择器或 RF 经济质量验收。

## 硬截止与旧测试评估

`test_parent_hard_deadline_kills_noncooperative_ocr_before_publish` 从2s改20s，ready 标记必须实到达、sleep30s、TimeoutExpired、无publish：仍能证明**测试拥有的外层子进程**被杀，并非靠改成不发生 timeout 得到绿；Windows冷启动余量的调整可以接受。但20s不是产品OCR配置时限。

产品 `LocalOCRAdapter.transcribe` / `enrich_pptx` / `NarrativeNormalization.normalize` 仍是同步原生调用 + 前后合作检查。外层 E2E Timer `os._exit`、pytest subprocess timeout 均是测试监督；仅凭它们不能声称每个产品入口都能硬中断。ROOT 已另行核对实际调用隔离/生命周期接缝，最终接受前应以实际入口 proof 和原生不合作反例证明按配置 deadline 回收，没有 orphan/publish。独立本审查未启动原生模型，也没有改部署接口。

其他诚实限制：det前所有未检出文字无法由该恢复器证明；真实页恢复仍需独立目视/回放；合成图没有产生同样低分分支是已报告限制，不当作真实测试替代。

## 边界与清理

- 产品代码、原工作树、原件、配置、共享 PWF 均只读；写集仅本 `independent/` 的小脚本/JSON/报告。
- 0 provider、0付费、0云 OCR、0模型下载、0原件打开。
- 探针只使用内存中的 synthetic PNG/PPTX；没有创建额外 scratch、数据库、缓存或模型文件，`-B`/dont_write_bytecode 防止 leaf pyc。
- ROOT 合并/真实 E2E/PWF/提交推送另管，本阶段不签其完成。
