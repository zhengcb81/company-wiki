# 三个已验收独立包并线发布（2026-10-31）

**IR、QA-RAG、MeetingConverter均已测试、并入各自主线、更新各仓PWF、提交并推远端。** [精确提交/保护收据](receipt.json)。不是只接收交付，旧“已验收未并线”状态被本记录替代。

| 仓库 | 当前发布提交 | 本次验证 |
|---|---|---|
| industry-research / main | 98640a9a | 67 unittest/2.701秒 |
| QAbyLLM / main | 1f551474 | 28重建/发布单元与真实临时Chroma集成/78.27秒 |
| MeetingConverter / master | 6c857a8b | 76输出与pipeline/1.30秒 |

三个原主线都仍在冻结起点，fetch确认QA/MC远端一致后快进，无合并冲突；代码全部是此前最终独审接收版本，后缀只发布文档。测试在ROOT新稀疏工区_merge_ir/_merge_qa/_merge_mc，只用合成输入，未复制生产库/音频/模型。MC原.coverage SHA6670792e…c5d9c前后完全一致，未暂存。作者树不改。

IR原本没有remote，同名地址只读返回not found。用户明确要求新建，ROOT用已登录GitHub创建[私有industry-research](https://github.com/zhengcb81/industry-research)，不添加README/新初始提交，再连正常origin推送本地主线。网页已显示Private、main和6commits；Git ls-remote精确等于本地。无凭证提取、无新token或全局权限修改。

QA原仓没有Git author配置，提交发布文档时沿用ROOT本任务已有身份，以单次-c user.name/user.email传入；不改全局Git身份。IR和MC正常提交。三仓各计划新增ROOT发布段，总控dispatch/CURRENT_STATUS同步。原作者历史handoff不改写。

原短测试命令/日志在ROOT .planning/older-packages-merge-20261031；不重复旧全仓/模型测试。QA旧PyPDF2弃用warning如实保留，非新错误。远端CI不从本地绿测推断。

**下一步已回M8来源主线。** 来源passage的疑问/礼貌句范围与业务因果共享owner仍需完成/独审，再真实源重放/摘要/缓存/RF。与此同时CWP946537d0的CI已实际失败（11例Linux平台接口/跨盘夹具），ROOT正在隔离根修，不将旧in_progress误报绿。W23-OCR-R1另是可并行实证返修，没在本轮启动模型。
