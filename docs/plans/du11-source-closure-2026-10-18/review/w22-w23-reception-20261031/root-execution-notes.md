# ROOT执行附记

本次初次暂存把已git rm的两清单再次git add，pathspec失败后shell仍继续commit，仅生成本地删除提交；立即精确stage实际源码并amend该自有未发布提交为946537d0，再正常pre-push167P发布。没有改写作者/已发布历史。

初次清理普通Win32路径无法lstat非BMP长路径；只对已核绝对owned测试根改用extended路径复核reparse后清理，最终absent。没有开全局长路径/ACL/MIC。

静态最终检查发现UTC常量置于后续import前的E402及未用导入，已机械修正并ruff全绿；fresh-process兼容测试初版del UTC在真实3.10会错，独审指出后改条件删除。Windows子进程首次出现解码thread warning，已显式-B/-X utf8，最终14P无warning；不靠压告警得到绿。
