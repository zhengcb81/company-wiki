# 安装器暂存接缝独立审查

**PASS / 0 OPEN（代码与本次定点范围）**，不代表真实目标安装完成。绑定提交 `f7aa0bab5fd110397ce31bfc7c7c069013cfa51d` 的安装器及测试两文件，LF SHA 见 JSON。

诊断栈与本机 Python3.14.2 标准库源码相符：Windows的 tempfile 在 PermissionError 且 isdir/os.access(W_OK)成立时会继续 TMP_MAX 候选循环。目录预检不能证明受限令牌实际可创建文件。新 `_stage_file` 只对 FileExistsError 重试、总尝试最多8次；PermissionError原异常立即传播。仍在目标同目录以O_EXCL/0600创建，没有ACL修改、备用目录或第二写通道；后续fsync、SHA、CAS、os.replace及清理路径在提交差异中保持。

独立短tmp探针在Python3.14.2通过5组：

- PermissionError保留同一异常对象，每次stage仅1次open，失败后目标snapshot不变。
- 真实既存碰撞文件让O_EXCL连续失败，准确8次后结束，既存文件bytes/mtime不变。
- 2次真实碰撞后第3次成功，fsync1次，仅所选SKILL.md改变，无新暂存残留。
- 第二个文件replace失败时如实partial：第一所选文件成功，后续未写；未选文件、用户config与旧目标bytes/mtime保持，失败暂存清理。
- 新stage接缝中的并发owner edit仍被CAS识别并保留。

全选择性安装测试实跑 **19 passed / 3 skipped，12.14秒**，不能写成22项通过。3个directory-link/alias/root-retarget案例因本环境 `Access is denied` 跳过；另有精确skip收据，没有修改权限或尝试替代通道。测试中的两处旧tempfile观察接缝已在ROOT反馈后改到_stage_file，原CAS/root所有权/cleanup断言未删。独立真实碰撞恢复探针补充了新负例测试只注入异常所不能证明的成功恢复行为。

仅写审查目录和自有短tmp，真实安装目录未写，ACL未改，所有自有tmp已清理。受限令牌仍可能对真实目标返回EACCES；这是实际OS错误，应如实报告安装失败，不能把本审查PASS或个人owner FullControl当成安装成功。无新增审批要求，也未建议绕过权限。
