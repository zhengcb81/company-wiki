# W08 pre-push ROOT修复：最终有限独立通过

同一份冻结中性断言与原case在 **Conda Python3.13.9** 下通过：**42P/0F/0E/0skip，2.00秒**，含20个独立中性例、原pre-push5个精确失败nodeid及原17个promoted独立断言。没有新增样本或重跑362项/全量pre-push。本次不重签W11，也不代表真实249页/14目标或W08所有剩余工作通过。

最终owner `src/company_wiki/source_catalog/narrative_predicate_state.py` raw SHA **`2ed1433ec5b227528bd5fad4083a7df642ca87bdb86a524d9ab092b6648e7460`**。完整source/tests raw/LF SHA与实际母src import位置在final-receipt.json；本轮13项source/test在运行前后字节一致。

## 原发现的修复

- **I08-01通过**：目标metric自身的project名词不再自充forecast marker；实际名词语法关系识别与真实verb complement分开。Projects reached/stood at/were、completed projects、have increased均不再被误记未来。真正We/Management project及projecting继续保持预测，公共policy不把它们当已实现客户/项目存量。静态检查仍在同一owner；没有给issuer/例句建白名单，也没有在两个consumer复制词表。
- **I08-02通过**：leading assumption改为按紧邻clause边界搜索，可以处理In this scenario/For planning等前置状语；三个原失败条件不再被洗成actual。被否定/拒绝的假设、独立句与分号后的真实实绩保持独立；显式未来auxiliary与真实条件共存继续保留原意义。

初轮原42项的34P/8F、stdout/JUnit与reproducible.py.txt都逐项SHA重核一致，未覆盖。修后final-reproducible.py.txt仅改变owner冻结SHA与final输出前缀，其嵌入20中性断言文本完全相同；原5nodeid也精确一致。原17仍直接运行正式旧文件，未复制/放宽期待。

ROOT新增正式grammar回归的另外4项仅静态核阅，不并入本独审42计数。本轮旧11个consumer/source/test均保持与初轮相同LF，且分别等于HEAD blob；这证明已有newline/stat状态没有变成语义改动。新grammar文件按修后实际SHA另行绑定。若后续仅Git CRLF→LF规范化，须归一后SHA仍匹配才能沿用本结论，其他修改不自动继承。

## 复现与恢复

```powershell
& 'C:/Miniconda/python.exe' -X utf8 -B 'docs/plans/du11-source-closure-2026-10-18/review/r1-w08-prepush-rootfix-20261024/independent/final-reproducible.py.txt'
```

该小源码保留完整20例、原case入口、禁网sitecustomize和清理逻辑；没有未留存的隐式fixture。历史产物须先保留到独立位置，重放会写final-*。真实命令、exit、实际import、source/test前后SHA及cleanup都在final-receipt.json，真实XML为final-junit.xml。

各进程collection前即阻断socket/connect_ex/create_connection/getaddrinfo（含loopback）、禁dotenv并移除API密钥环境变量；0网络、0原件、0模型。独占.planning/r1-w08-prepush-independent-20261024初始不存在，核其绝对父路径后仅删该目录，本轮结束不存在。

未编辑产品或正式新旧测试、Git、PWF、旧报告。**本有限共因修复验收通过并冻结；ROOT可继续正常hook/commit/push，大门结果仍由真实执行决定。**
