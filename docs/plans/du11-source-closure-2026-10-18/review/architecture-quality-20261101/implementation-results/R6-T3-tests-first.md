# T3 阶段 A：去公司化 tests-first

状态：**T3阶段A测试/夹具已冻结，真实RED已记录；未实施产品修复**。`tmp/architecture-r2/tests/unit/document_understanding_note_scope/` 在创建前确认不存在；本作者独占该新目录，不改 production、其他测试、Git/index 或主PWF。基于原R4-context调查及R6-T3实施细则，所有资料为内存合成来源，没有运行原件/模型。

准备范围：TERM双owner完整句/closing wrappers；真实编号与原生HTML heading正控；NOTE甲乙甲、同actor新备注、长/换行引介及真实source paragraph成员proof；PHYS跨页正负proof与局部未知；table/guide/furniture反控。只用现存接口，不import尚不存在的新模块，不用假heading hint让备注测试变绿。正式reading_context/模型fragment和真实H1仍属后续阶段，不由本轮结构RED代签。

## 实际基线与运行

运行工区 HEAD=`a6841e9420dbe3eb6dac6e30563c29e4293a31e7`。ROOT另已发布快检1bf3d388，不以该主线SHA假冒本轮候选测试基线。新目录仍为未跟踪；**这些文件没有跟随R4来源作者提交，ROOT后续应按该精确路径stage并配合产品修复**，本作者不stage/commit。

只执行一次整组：**47 cases，28 failed / 19 passed，4.66s，pytest exit1**；无collection error、无missing-module error、无xfail/skip。完整每case状态及failure原文保存在同名JSON；整轮宿主进程wall7.831s，与pytest测量口径分开。

```powershell
& C:/Miniconda/python.exe -B -X utf8 -m pytest tests/unit/document_understanding_note_scope -q --tb=short -p no:cacheprovider --basetemp C:/Users/郑曾波/Projects/company-wiki/tmp/t3a-913d0e50/r --junitxml C:/Users/郑曾波/Projects/company-wiki/tmp/t3a-913d0e50/results.xml
```

这是已完成历史命令，目录已删除，不应原样复用；下一轮选择新的owned短根。Junit SHA=`b090963ad425925e1a32aef3fadb16480f8306eb1f846572b200d243dcaf3afc` 以同名JSON实际记录为准（原XML位于已清理的owned根，其完整case文本已投影保存）。

## RED归因及既有正控

| 组 | 首轮实际 | 已证明的问题/边界 |
| --- | --- | --- |
| TERM | 18F/14P | Arabic/中文编号完整句加不同闭包装符后仍被adapter或layout错判标题；原无包装正文、Arabic adapter、真实短编号/真实HTML heading等正控仍工作 |
| NOTE | 7F/2P | 其中6项是真产品缺口：甲乙甲/同actor/重复跳号旧尾句祖先污染，长/换行intro丢失，valid source membership无bbox也无法保留intro；guide/furniture正控通过。另一项是下文已修夹具错误，不计产品RED |
| PHYS | 3F/3P | 实际page_neighbour可证明完整句跨页；结构仍丢本note intro，page gap/column冲突无proof后仍声称complete。deferred页不借intro及零work停止等正控通过 |

共 **27项真实行为RED**（TERM18＋NOTE6＋PHYS3），没有用预算抬高、改产品、假heading、fake proof或删assert换绿。

### 唯一夹具修正及一例复核

首轮table_footnote在进入结构前被 `EvidenceCoordinates` 正确拒绝，原因是把paragraph_index与table_index两种互斥坐标同时传入。这是本测试fixture的构造错误，不是产品缺陷；原失败记录原样保留。

已将该合成HTML脚注的table关联放入现有HTML producer metadata `table_index`，保留单一paragraph locator，实际adapter仍投影真实table_id。未改scope断言。**不重跑47整组**，只补该nodeid：**1 passed / 3.41s / exit0**。同名JSON分别保留first_run_files_sha256与delivery_files_sha256，只有fixtures.py因此有已验证的窄delta；不把首轮统计改写成“整组当前全绿”。

```powershell
& C:/Miniconda/python.exe -B -X utf8 -m pytest tests/unit/document_understanding_note_scope/test_local_scopes.py::test_guide_table_note_and_furniture_are_not_new_local_note_parents[table_footnote] -q --tb=short -p no:cacheprovider --basetemp C:/Users/郑曾波/Projects/company-wiki/tmp/t3f-a47043e1/r --junitxml C:/Users/郑曾波/Projects/company-wiki/tmp/t3f-a47043e1/result.xml
```

## 夹具强度与不能冒称的能力

- source IDs/hash由合成原始文本确定，unit ID和locator由既有`_make_unit`/EvidenceCoordinates构造；pipeline前后核source/raw/text SHA/坐标/locator/metadata不变，所有结构refs属于原始成员。它们是可重现parser observations，**不是已经读验真实PDF字节的证据**。
- 备注fixture没有heading_level/heading_like。HTML正控先由真实normalize_document解析h2，后运行真实understand_units；不是为备注伪造native hint。
- 无bbox正控的 `pdf-paragraph-membership/1` 来自真实align_paragraphs产物。验证accepted_groups=1和双向previous/next/group一致后，仅省略可选geometry/native-view；raw/IDs/locator保留。已执行到最终“intro缺失”断言，证明producer proof夹具有效；失败不能归为根本没有proof。
- 跨页正控先用同一次pipeline借用的真实NativeSourceContext证明observed_adjacent_page_flow与source/页/column/endpoints，再查真正SectionBuild输出；未塞任何正确section或手写page proof。跨页“本公司”没有被fixture解释为issuer。
- `inherited_heading_ids`仅检查实际结构祖先，不是生产替代闭包；正式citation view/support/context、material fragments、cache、公开handler和RF实际采用仍OPEN。正向intro必须保留，不允许仅forbidden旧尾句消失就签通过。
- 原R4九对与真实H1是否有充足原始成员/字符/DOM/物理证据仍OPEN，本轮未读取或重放它们。缺bbox不是通用权限门禁，只有确需该项推断却缺证的scope关系才partial；原文预览/复用不在本测试阻断范围。

## 隔离、清理与源码冻结

两次都是normal host `C:/Miniconda/python.exe`；独占basetemp53字符，日志明确未relocate，outer pytest cache provider关闭。新根在创建前absent，解析后containment及非reparse核对；只删除本次新根：

- `tmp/t3a-913d0e50`：删除前52,909逻辑B，after=false。
- `tmp/t3f-a47043e1`：after=false；仅一例夹具复核。

未创建真实PDF/模型缓存、DB或公司资料；没有无法归属目录的猜测删除，没有全量恢复演练。5个实际依赖的结构owner SHA在整组测试前后完全相同，完整值在JSON（adapter/layout/sections/narrative_continuity/pipeline）。语义作者的在途文件未改。

Ruff检查新目录通过；未跑全unit、旧测试目录、原件或模型。新增目录6文件共冻结如下：

| 文件 | 交付SHA-256 |
| --- | --- |
| `__init__.py` | `56027e62eb0cfed0fefdb75fdb2aa0936300c09ca4521e76a12dbec25a86598e` |
| `fixtures.py` | `6762dac9eba99a34d384844d865f5ef5f6bd2d76889e6d6f12567dbc4e5ec2bf` |
| `README.md` | `6329dd8089c8e85edb200e694e7a91868ebb0321851259308f031d3439f5effd` |
| `test_local_scopes.py` | `4ec8718a11e7bf87adadc26341abf3fab3eee7744c9884729c70bcafe83331ae` |
| `test_physical_scope.py` | `e6dae64bf6830a0cfbdc2ce7440cc04d6f2b2a19392c6bbfae946841b4d6cf45` |
| `test_terminals.py` | `277982d57448a7b2998b216da7784aa55eb273252693477f49e64ded82bd829d` |

ROOT待R4节点收口后按已有T3细则在对应owner实现；本作者到此 **STOP**。此目录当前有意保留真实RED，不能单独当作绿色产品版本发布。
