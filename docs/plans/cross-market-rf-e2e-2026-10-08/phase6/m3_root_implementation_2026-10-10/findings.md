# Findings

既有HTTP adapter只留finish_reason/content_bytes，失败final和完整响应SHA均丢；caller结算后失败HandlerResult.result={}，批次仅读metrics，需贯穿同一既有attempt数据而非新旁路库。纯诊断不得覆盖原模型/预算异常，空间依原持久/输出预算。
