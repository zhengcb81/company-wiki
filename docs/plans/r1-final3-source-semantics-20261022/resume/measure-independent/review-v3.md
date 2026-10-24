# W08 measure 第三轮独立复审

结论：**PASS_BOUNDED_ENGINEERING**。既有四组固定探针与抽取架构检查全部通过，本节点已定位的问题未再复现。此结论不代表整份249页原件内容通过。

## 实际执行

| 固定组 | 结果 | 退出码 |
| --- | --- | --- |
| 原51项关系/事实投影 | 51P / 0F | 0 |
| 原14项候选/最终选择 | 14P / 0F | 0 |
| 第二轮26项holdouts | 26P / 0F | 0 |
| 第二轮16项候选/最终选择 | 16P / 0F | 0 |
| 意义抽取/指纹架构检查 | 10项全部通过 | 0 |

共77个固定关系/投影样例和30个集成样例；集成组复用了语义样例，不应宣称107个独立语义样例。本轮按ROOT要求未新增语义扩面。完整运行、stdout和逐例结果见 execution-v3.json 与对应 *review-v3.json。

## 修复与架构核对

- 因果消费者 `_measured_driver(clause, after=link.end())` 在完整来源句子上消费关系并按原始offset筛选，保留句首条件/否定/模态；未对子串重建“已观察”状态。
- 测试过的冠词/物主词金融组件、will/expect/next-year未来数量已被共同measure owner挡住；独立当前数量与另一分句计划共存的正控仍通过。
- policy导入的11个意义函数/常量与 narrative_business_meaning 对象identity相同；policy与meaning无重复函数/类定义。purpose使用同一意义函数；meaning无policy/purpose反向依赖或IO导入。
- decision_inventory实际business_algorithms列表包含新meaning模块。仅在内存mock该文件读取加标记，使business指纹由 `1e2b626d62dec02285932cd6abed58e85f78c8755621ec1455e76694ebc7515d` 变为 `2eff8b40d6bf1e352b1d8d424d985e50ee06f89654fbd2abac12eb8d2ea35eee`；真实产品字节未改，预算策略仍reading_plan/3。

抽取等价性结论限于同对象复用与固定回归通过，不声称所有可能来源文本上穷尽等价。

## 哈希绑定与证据

- policy：`2b76f3920546f7ca5060c56d5723c60663f88aa98dd16a073c290559349499f3`
- meaning：`3cef483033d1b54e4fe6aa908cfd129fc3d370bdd5b89f915eac12cb47fc92cb`
- purpose：`e19fb73bc96c88d5c32930f747d27475841ee6f97478072fef41a9a0c57658e4`
- decision_inventory：`44aa51750047a46ddc31dece234debbea86d5cb19f83acf8974ebbea489f3e9a`
- semantic_value tests：`a7e28f6c0157750cb2eb389c70239d5f01d9fff40b278583a8862cb6939cc976`
- measure_scope tests：`1c0ee3269665edd8edb4a63769c9942c064d0530b383d50ac81fb1ce1678c29b`

四组执行前后所有依赖SHA一致；架构执行前后四产品SHA也一致，reading-business-policy/13。旧v1/v2全部保留，清理与旧证据哈希见cleanup-v3.json。无产品/配置/原件/Git写入、网络/API或下载；bytecode写入禁用，无输出目录pycache。

架构探针首次自有编码名写错utf8-sig，保留原错误script/stdout；改为utf-8-sig后完成有效检查，该错误不计产品失败。作者集中suite、Ruff/mypy由ROOT负责；此报告不会自动覆盖后续源码变动。
