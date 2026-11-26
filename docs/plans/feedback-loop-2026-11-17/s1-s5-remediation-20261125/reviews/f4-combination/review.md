# F4 组合独审结论

三组使用同一版本的 F4 宿主，均通过。先验证独立候选，再从下列已发布 Git 提交重跑。每组测试使用独占目录、合成输入及真实本地命令入口。

| 模块 | 实测版本 | 同号恢复和去重 | 收据 |
|---|---|---|---|
| filing-fetch | 4bd76b393dde | 两个出箱同时不可用后，宿主补投并登记原五条。后续新增零条，业务替身执行一次。 | [FF](ff-result.json) |
| industry-research | 38345b663a33 | 宿主自动补投同号原观察一次，完成观察、分诊、修复、复验和回告。两次宿主冷读均与 owner 结果一致，另一运行号保持未知。重复补投零条，原报告和原审核输出字节一致。 | [IR](ir-result.json) |
| earnings-transcripts | 672ed1012e27 | 进程创建拒绝后保留真实 CLI 原结果，F4 登记原五条并确认接收。两次冷读均为失败且费用不适用，错配身份保持未知。启动一次，网络请求和响应字节均为零。 | [ET](et-result.json) |

IR 的原组合红例来自公开响应形状。owner 成功对账时已返回结果，但缺少宿主读取的状态字段。总控将完成状态写入同一个成功响应，未知状态沿用原义。原红例另存 [失败收据](ir-red-result.json)。

IR 对账修复已在 `38345b663a33d5c57b557bf4d193a8baa9149d41` 推送，公开响应脚本 SHA-256 与验收收据一致。FF 的后续 `4bd76b393dde08e9915390de1d47950f2e3b9705` 只修复矩阵测试和补写计划，组合实测调用的生产脚本字节一致。

## 复跑命令

在 company-wiki 根目录执行。试验目录中的脚本按表核对各 owner 工作检出的提交，再使用独占数据根运行。

    python -B .planning/r25/combination/ff_probe.py
    python -B .planning/r25/combination/owners_probe.py ir
    python -B .planning/r25/combination/owners_probe.py et

可重复冷读使用真实 F4 LocalHost RPC；落盘计数只读核对隔离宿主账本。IR 修复只写自己的派生产物，ET 注入启动故障的夹具禁止任何供应商网络请求。未运行真实供应商或部署定时任务。
