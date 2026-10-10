# P7 独立施工包准备

## Goal

划出真实待修共因的三个独立较大责任包，配齐工作树/独立PWF/排他源码写集/测试和交接。MAIN保留AUTO共同接线、并线与定点安装。

## 大节点

1. 最新PWF/源码/真实待修根因调查：complete，三独立只读调查，旧已完成M3不重派。
2. 精确接口/写集和三个独立目录/本卡PWF：complete，仅启动文档正常commit，source实现未开始。
3. 集中包审查与交付完备性：complete，独立跨卡复核及54项启动/格式/隔离校验PASS。中央文档正常发布的实际回执另见publication.json/exact-ci.json，不用计划代替真实结果。

## 可启动卡（只有这三个）

见README.md：P7-CWP-PROJECTION / P7-RF / P7-AUDIT。三个实际目录、branch/sourcebase/最新bootstrap HEAD见lanes.json。用户可现在并行交给harness；本卡文档已备齐，不等MAIN或另一卡的新接口。

## Errors

- 新RF checkout体积预检发现跟踪870,118,781bytes；改复用已有本任务干净树，避免额外复制，旧分支保留。
- 实际PWF解析在Windows PowerShell5.1因缺IsPathFullyQualified返回空（exit0并非成功）；改用本机已有PowerShell7，三卡均实解析到各自PWF。未修改安装技能。

## Next Step

将三张唯一施工卡/工作目录交用户，由MAIN继续自己的AUTO责任TDD。中央文档发布以publication.json/exact-ci.json实际观察为准。默认0外部provider/model/新增费用。工程未实施，不核销真实研究。
