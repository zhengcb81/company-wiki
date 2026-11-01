# H1真实回放原字节证据

本目录仅保留本轮小型观察收据和启动前runner/cases/comparator输入快照，不含PDF、数据库、费用账或完整恢复备份。JSON以gzip保存，避免Windows Git文本换行改写原观察SHA；MANIFEST记录压缩与解压原字节身份。未执行解压恢复演练。

v1为较早代码的12unit/111member观察；v2为公开合同FAILED，不能被R5小合同测试改签PASS。原件/DB/WAL内容与mtime不变，SHM只mtime同步。v2-inputs清单绑定三份启动前gz，不把后来修改输入当原启动版本。

当前可恢复工作入口仍为本repo `.planning/architecture-quality-20261101/real-acceptance/`；脚本ROOT采用该目录层数定位，**不要在本archive目录直接执行**。未来需重建仅runner/cases/comparator等测试程序到该预设工作目录，先复核原件SourceRef和当前配置，输出另名v3；不恢复旧数据库、不复制PDF、不覆盖v1/v2。代码版本/源样本由SOURCE owner读，当前暂停不重放。全深度schema2检查点见v2 cases快照，其他文种更深oracle仍需完成，不称已验收。
