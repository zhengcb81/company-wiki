# Legacy post-adapter 根因诊断

结论：**历史部署fixture与真实依赖身份不一致；本失败未证明生产cache身份缺陷**。

1cddb0bd把structure身份从加载module.__file__的列举改为decision_inventory同级真实structure/*.py全部物理源码，覆盖未来子算法。旧测试仍只exec历史.txt并改sections.__file__，未部署真实旧物理包。

独立仅一次原节点加只读观察，25.17秒复现line125（请求1≠2）。old-a实际旧code filename和module file为legacy.txt（LF7f010cc…），但实际_structure_algorithm_hashes返回当前物理sections身份abddf859…；new-c真实current模块仍返回同abddf859…，整个structure映射digest同为e8325e…。old-b/new-c均reused同一artifact且0token，structure观察行始终1，新算法从未执行。old/new公开bundle与Ref完全相同。保存实际bindings/final generation、bundle及model material，见comparison及各snapshot。

旧final记录business_algorithms=d35e6ae…，decision_digest=c1eeab9…，当前current_reading_decision_matches确实为True。该旧final的身份认证了当前物理包，不能代表真实旧部署。独占物理包负控制只将sections.py换为历史字节，现有hash owner正确给出旧7f010cc…，仅该键变化；无需修改生产hash。起因已由git show1cddb0bd确认。

应在自有fixture部署实际decision_inventory及structure物理包（只把sections.py替换成历史字节），让旧算法执行来源与依赖owner读到的字节一致；现代阶段恢复真实当前包。保留全部2POST、不同material/上下文、新缓存恢复及旧ref不变断言，不伪造cache版本常量、不放松产品校验。ROOT随后已明确授权本agent仅修该测试文件；该实现与GREEN另存，不作为本报告独立验收。

诊断过程6文件SHA前后一致；无生产/原件/配置/断言写入，无下载/真实模型。ownedPID15556不可见，观察tmp与负控制overlay均恢复不存在。原RED完整trace和XML保留，其他cache修复不在此报告签收范围。
