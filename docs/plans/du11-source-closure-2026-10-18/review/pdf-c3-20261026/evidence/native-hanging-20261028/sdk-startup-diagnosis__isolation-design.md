# Docling依赖运行时隔离：只读设计

建议配置一个标准、无system-site继承的专用venv，并从现有安装按**既有resolver选中的distribution闭包**创建文件级NTFS硬链接视图。运行配置的python指向该venv，模型artifacts继续指向原目录。这样复用原Python标准库/DLL、SDK和模型字节，将第三方metadata可见集合从当前426项缩到实际104项，不复制GB级SDK或模型。本轮未创建venv、链接、配置或SDK进程，仅写本设计md/json。

这项隔离减少的是已经实测的导入元数据枚举面；没有证明隔离后能够在120秒内完成真实SDK启动。当前已审PDF四文件无需为本设计改动，120秒/4GiB/3页/2MiB/CPU4继续保持。

## 本地证据

此前唯一30秒cold探针的三次栈均在Transformers5.18.0顶层 `packages_distributions()`，未返回Docling首import。该Python3.13函数遍历可见distribution，缺top_level.txt时从RECORD推断并逐路径exists。本轮没有再调用SDK或复跑该耗时扫描。

使用现有 `configured_runtime_roots → describe_environment` 只读解析声明依赖、marker及extra，得到**104项distribution**；环境SHA重算为 `c84a984ccb3a56dffbfd0d4538f14ce4a27de44dec4981527a2b0c4a545cdf44`，与当前runtime-4g-v2.json完全一致。这比另写一份“Docling应该用哪些包”的列表更可靠。根仍是docling、docling-core、docling-ibm-models、torch、pymupdf、pypdfium2。

这104项中43项缺top_level声明，RECORD合计36,228条、53条位于site-packages外；因此不能承诺扫描归零，也不能只链接Python代码而漏掉数据、native模块和资源。读取的RECORD字符串统一换行后约3.37MB，不能直接当磁盘stat容量。mkdocs-material、gradio、langchain、kubernetes均不在闭包中，隔离可以排除这些额外metadata；没有通过删全局包来实现。

本机C盘为NTFS。Python3.13本地venv源码使用小型Windows venv launcher并共享base interpreter，现有venvlauncher.exe为253,256bytes；`site.py`在 `include-system-site-packages=false` 时只添加venv site且关闭user-site。这里只核了源码，没有试建venv或链接。现有Conda pkgs目录未发现docling/torch/transformers名称项，不能假定已有完整离线Conda包缓存可直接重建SDK。

worker显式加入的repo/src当前还含 `company_wiki.egg-info`。因此104是第三方SDK闭包数量，不能武断要求整个进程只看见104个metadata对象；应用自身metadata应作为明确、单独绑定的应用来源允许，不能为追求这个数字再造import loader或改已审worker。验收应排除未经声明的第三方distribution，并核所需104项闭包，而非误删第一方metadata。

## 实际方案比较

| 方案 | 是否排除无关metadata | 大文件重复 | 判断 |
|---|---|---|---|
| 专用标准venv、无system-site，按选中RECORD做文件级硬链接 | 是，目标104项 | 不复制SDK/model内容；少量launcher/目录/manifest | **首选设计**；使用已有配置python定位，兼容标准site和metadata |
| 专用exe + `_pth` + 同样的选中文件视图 | 可更严格限制sys.path | 同样可复用文件 | 备选；Windows DLL/launcher/_pth优先级及site hook行为尚未验证，比标准venv增加启动机制 |
| 全新精简Conda环境，从已有离线包缓存安装/链接精确版本 | 理论上可以 | 包缓存足全时可链接 | 长期部署选项；当前没有证据证明SDK完整离线工件已在Conda缓存，不能在本轮假设可用；clone整个现有env仍含426项 |
| venv开启system-site、向 `.pth` 加回整个Conda site、仅用 `-I`/PYTHONNOUSERSITE | 无法排除interpreter自己的全局site | 无 | 不能解决本次全局扫描；`-I`本身仍允许该解释器正常site初始化 |
| patch Transformers/metadata或伪造top_level.txt，卸载全局无关包，保活常驻worker | 不属于干净运行时配置 | 不确定 | 不采纳；会改第三方/全局行为或生命周期，不能替代依赖隔离 |

专用venv中不得用一个目录junction把整个 `C:/Miniconda/Lib/site-packages` 暴露回来。顶层package目录junction也只能在确认所有权独占、来源固定时考虑；默认文件级硬链接更可控，不依赖管理员symlink权限，仍须未来实际验证目录写权限和链接能力。本设计没有改ACL或创建链接。

## 一个必须保留的真实迁移边界

对现有RECORD做只读所有权比较发现，选中python-pptx1.0.2与未选中pypptx-with-oxml1.0.3共用 `pptx` 顶层目录：110个共同路径中9项RECORD hash不同。已读取前6项实际小文件核对，均匹配选中python-pptx、未匹配另一个包；其余未在本轮全部验完。

这说明不能把顶层目录或“安装过的metadata”当作完整包字节来源证明。部署投影应只带选中RECORD拥有的文件，遇到包间冲突或源字节不匹配时报告并停在部署层，不能顺手把另一个distribution加入依赖闭包、复制不明目录或重标原环境SHA。43项缺top_level的包也不能为加速而补写伪造metadata。

## 保持职责与配置契约

- **闭包owner**仍是现有 `narrative_pdf_environment`：Requires-Dist、extra、marker、版本规范及完整性检查照旧，不新增resolver或摘要业务逻辑。
- **部署owner**准备新运行时目录、按已选metadata生成硬链接/资源投影和来源清单。基础解释器、包字节与模型目录必须有稳定来源及显式更新步骤；硬链接共享原地写入风险，目录junction则会随源目录替换一起漂移，不能称其天然immutable。
- **配置owner**写新的显式runtime/2 profile，python改为专用venv；原artifacts/model SHA/config SHA及实际预算保持。验证同104项和环境SHA后才采用该profile，不能仅换路径就宣告部署成功。此任务没有改生产profile。
- **启动环境owner**保证没有通过PYTHONPATH/PYTHONHOME、user-site、sitecustomize或执行型 `.pth` 加回base site。当前父层会继承环境，配置仅有python路径、并无任意解释器参数；不能把 `-I`等参数塞进python字符串。可在部署启动环境清理这些变量；若需工程化，则由现有PDF运行时环境构造owner集中承担，而不另建launcher/任务库。项目worker本身已能显式建立repo src路径，不需要复制整个应用安装或继承无关editable `.pth`。
- **运行owner**继续有限cold worker、单converter、源/SHA/版本/recipe绑定、原生fallback与partial协议。没有新增常驻worker、缓存、provider或第二调度状态。

既有environment/2指纹绑定版本、metadata依赖、extras和marker环境，**不哈希全部Python/native代码字节**。同一字节投影应重现同SHA；Python patch版本、依赖metadata、extra或版本改变则必须重算并显式换配置。投影来源清单可以记录RECORD及必要实物hash，不能夸大现有environment SHA已解决全包字节防篡改。模型继续复用原目录及独立model/config SHA，不搬运权重。

## 可执行后续步骤与验证边界

1. 用当前既有resolver冻结104项完整描述及选中metadata来源；按两种斜杠规范化RECORD，规划只在新env前缀内的site-packages、Scripts和确需资源目标，拒绝路径逃逸。53项外部路径不能盲目丢弃，也不能直接写入base/global位置。
2. 在部署自有目录准备无pip、无system-site的标准venv；从既有源按选中RECORD创建硬链接，完整保留metadata和package资源，命名空间逐文件合并并核冲突。不执行在线install、全局卸载、SDK或模型复制。
3. 明确native DLL来源：当前Conda的Library/bin可能仍是合法运行依赖。复用这些具体DLL搜索位置不同于把base Python site加回sys.path；需检查实际模块/DLL来源，不能为修一个import而暴露全局426项。Windows launcher/权限/加载行为在本轮未部署实测。
4. 先做轻量、无SDK元数据验收：新解释器的sys.path不含base/user site，第三方metadata集合仅选中104项，另明确允许并绑定repo的company_wiki应用metadata；现有resolver输出/SHA一致，四个排除例缺席，选中文件冲突已闭合，artifacts原路径/hash与120s/4GiB等额度不变。源变更或指纹不符不能静默退回全局SDK。
5. 设计采用后再安排一次有界无文档cold启动和独立部署复查，随后才做原计划正式真实验证；不能用“104项可见”替代SDK能启动、也不能用无文档启动代替PDF闭合及摘要正确性。**这些部署和SDK验收都未在本任务执行。**

本轮除两个isolation-design文件外无写入，无新增coldprobe、原PDF、下载、收费或全局环境改动。所有数量与比较依据、风险及未验证项在同目录isolation-design.json中结构化保留。
