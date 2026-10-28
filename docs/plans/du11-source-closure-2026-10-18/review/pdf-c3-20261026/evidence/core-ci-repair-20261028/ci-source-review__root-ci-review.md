# ROOT CI三文件独审

PASS / 0 OPEN。本审查者未编写这三项delta；另行编写的operating-state grammar不在本独审范围内。

9项定向验证通过/2.70秒，测试前后3文件LF SHA一致，见JSON。全局40在salvage与per-task2之前校验，逐task仍在salvage前严格执行；自有无效41条、无效/有效混合3条和2条内整条丢弃反控通过。没有放宽上限或吞错误。

当前生产协议fixture从resolve_model_boundary读取，避免重复旧版本字面值；新增stale prompt不能恢复，原request/hash/output/blocked/不同projection反控保持。历史v3代码未改；这不是使所有历史pin自动按当前协议恢复。

歧义数表原文18、quality flag、constraints原断言完整保留。完整source plan和source_table_unresolved可查，但模型事实support不再借这数字；完整native表映射仍精确可用。此项是PWF新合同，原后半“歧义数字也必须送模型”过期，并非删除原文。

自有.c3cir恢复不存在，0PDF/网络/模型。仅定向验证，不代签远端全CI成功。
