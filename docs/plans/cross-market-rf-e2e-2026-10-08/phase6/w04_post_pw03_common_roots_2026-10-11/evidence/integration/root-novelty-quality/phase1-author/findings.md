# 发现

初始代码coverage_tokens只含英文/中文shingle，独立数字被丢弃。budget将所有span tokens无序并集，min集合50%重叠在stage/score前排序，未能证明完整组重复。finalizer逐span提取，没有跨行完整组保护签名。canonical CodeGraph索引未含本树这些新WIP，首次结构查询返回无关旧符号；随后读取已指定文件。

Git只读普通沙箱status误报not a work tree；正常提权只读确认HEAD35a9a645与ROOT既有WIP。未执行任何Git修改。

首次RED共有31 FAIL，其中25个integration由于测试fixture parser_version不是semver，不能作为产品反例；原日志保留，已改fixture为0.1.1并将完整package dataclass直接比较。单位6个为真实行为失败。重新固定正式RED，不将夹具错误归于产品。

最终共同机制：finalizer在保守dedup后按native order_key一次拼接完整group并共享signature给所有成员；最多8193临时字符，超过8192标incomplete；512token/保护句/stage上限。纯budget只读metadata，不能读payload或文件。保留事实完整句而非数字集合，因此同组不同主体的300/500互换不会被判重复。stage_signals沿用已有公共predicate的stage/predicate/realized/diagnostic；未知actor不冒重复。只有两侧均达到85%文本覆盖且保护句、阶段信号同序一致才软降级。该提示比语义等价保守，可能错过同义复述去冗余，真实budget收益仍需ROOT实测。

既有3个手造tokens单元正控改为公共coverage_signature真实文字输入，断言保留；新增35项公共分词/finalizer、数量/单位/主体/阶段/否定、跨行native9→10、PRISMO新增事实、短subset、缺主体、截断、纯budget不读IO。集中365PASS；禁用第三方插件的合成环境只有asyncio_mode配置unknown一条警告，非产品失败。没有修改pytest.ini或全局门禁来消警告。
