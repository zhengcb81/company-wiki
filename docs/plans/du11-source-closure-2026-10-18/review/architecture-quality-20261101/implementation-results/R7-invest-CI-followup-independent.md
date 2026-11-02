# R7 invest CI 四文件独立增量审查

结论：**PASS**。没有发现需要返修的问题。本结论只覆盖四文件 fixture/测试环境改动，不代替完整远端 CI、真实公司或已安装技能部署验收。

作者报告 SHA `bd9346d8cf8ba3bbabb271df1cd7d2f9aea0be0f3a6b3b9653bc48161ab4e483` 已核；四交付文件、此前其余 12 路径、RF 四份既有 WIP 的 SHA 在独审前后全部匹配。canonical `invest_contracts.py`、RF `schema_compatibility.py` 及其真实验证函数没有修改；明细见同名 JSON。

## 独立控制

新增 8 项反控，首轮 **7P1F / 1.06s**。唯一 F 是独审 subprocess 使用 `-I` 后环境 UTF8 选项被忽略，中文路径输出的编码与父进程不一致；对子进程显式加 `-X utf8` 并明确解码后，仅重验该项 **1P / 1.03s**。没有据此改产品。原真实 framework 失败点另独立执行 **1P / 1.33s**；未重跑 144/690。

- 两份真实 builder 分别接受未来 provider 标签及未来 receipt formatter 的 engine 标签，仍通过 RF 公开 matrix 选择 schema 3.4 的已文档化 emitter（当前 3.5.0）。provider 返回字典及其 input_document 不被修改。
- 实际 RF output validator 接受投影；通过真实 invest adapter 后仍明确 `legacy_read_only_validated`，不是 current_validated，签名仍为 unattested。
- 当前结果被分别篡改 input currency、output unit、source SHA、数值千倍、result SHA，真实 `invest_contracts.validate_revenue_forecast` 均拒绝。前四项即使重算最外层结果 hash 也不准入，没有放宽兼容或数字校验来修 fixture。
- fresh 子进程先加入真实 installed 路径后加载实际 root conftest，仍绑定仓内 canonical contract；另一个明确选择 installed 路径且不加载 root conftest 的 fresh 子进程，仍能独立加载已装模块。测试路径绑定不会变成对部署目录的运行时许可或全局替换。
- 原实际 framework 用例直接经仓内 root conftest 执行，明确 legacy_read_only_validated 且无 current workflow receipt，不依赖本次独审预载模块。

## 设计核查

版本 pair 由公开历史 emit matrix 选择，固定 legacy schema 不跟随移动 current ENGINE_VERSION。projection 的说明准确：它用当前合成数据重建一致 receipt/hash，只证明旧 schema 的只读兼容输入，不声称运行历史 binary 或持有历史实物。两份 builder 字节相同，deepcopy 及公开 load 返回副本避免污染 provider/cache。

conftest 在 collection 前关闭生产 dotenv 和无意义默认 signer，session registry 保持独占临时；显式签名反控仍可自行配置有效 provider。canonical 绑定用于避免测试被 HOME 副本遮蔽，不改变 production compatibility/crypto 校验，不要求用户签收或全树 clean。没有新增 skip、豁免或修改原 framework 期待。

## 清理与范围

所有写入只在自有 `company-wiki/tmp/r7iv-independent` 及独审报告/日志。CWP pytest 的两次独占 basetemp 均有 removed=true 收据；framework 自有 basetemp 及测试源码在归档后，使用 fresh Path.stat 核实文件、绝对 containment、无 reparse，仅删除该目录恢复初始 absent。未根据缓存 DirEntry/nlink=0 误判文件；无用户数据、他人临时文件或 Git 目录清理。

没有修改 invest/RF 源码、配置、全局安装或 Git；没有密钥、原件、下载、模型及付费 API 操作。ROOT 可正常提交推送，以新的真实 CI 收据关闭发布节点；本线 STOP。
