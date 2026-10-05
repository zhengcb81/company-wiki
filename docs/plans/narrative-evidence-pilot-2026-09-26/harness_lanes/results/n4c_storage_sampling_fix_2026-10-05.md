# N4C 空间采样竞态修复

## 发现与修复

run03使用既有Config加载国内MiniMax-M3/8192/温度/reasoning，仅一份P04招股书及English IR policy。批次返回`NARRATIVE_BATCH_FileNotFoundError`，**模型预留、调用和新增费用均0**；policy select/summarize/verify成功，P04 select未完成。没有新RF实读。本次CLI未保存异常栈，不能将这次FNF唯一归因于一个位置。

离线检查发现`narrative_batch._tree_bytes`对每条路径先`is_file()`再`stat()`；SQLite SHM及原子对象临时文件可在两个操作之间消失。两个确定性RED分别用SHM和object临时文件复现FNF。改为单次stat，只有FileNotFoundError计为已释放；PermissionError继续可见。模型、协议、正文选择、费用和容量上限均未改变。

31项批次/请求责任测试GREEN；正式CLI+真实spawned Worker+loopback HTTP故障注入1项GREEN（4.75s）。测试确实在采样中删掉独立临时文件，仍发布final且仅一个本地模型请求，未知/未结算费用0，原件和foreign jobs不变，测试根finally恢复。Ruff通过。没有增加日常全仓长测或人工签收。

## 失败记录和目录恢复

临时实验driver另有诊断连接未显式close；SQLite的connection context manager提交/回滚，退出并不关闭句柄，导致Windows cleanup WinError32。进程退出后，恢复保留[run03账本与安全诊断](n4c_live_2026-10-05_run03.json)，再删除经过绝对路径核验的`tmp/n4live05c`。四份真实原件SHA及用户配置SHA核对一致；原先内存中的峰值/耗时/生产前后fingerprint丢失，收据明确记为lost_observation_fields，未伪造数字。

driver现显式close，并在删除scratch前先写小型费用收据。run03为零，不增加既有33,660tokens/16,580microUSD。国内官方费率及保守FX历史余量2,764microUSD见主PWF；下一run04仍只P04+policy，26,340tokens/80,656microUSD，沿用配置。N4C尚未完成。
