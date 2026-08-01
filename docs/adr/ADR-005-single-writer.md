# ADR-005：唯一 WikiRepository Writer

> 现行范围见 [ADR 适用范围说明](README.md)：single writer 只允许 source-oriented projection，legacy 研究 Wiki writer 冻结并待退役。

- 状态：accepted
- 日期：2026-07-10
- 背景：当前多个脚本直接写 wiki Markdown，没有统一入口，无法保证原子性、来源计数和人工注释保护。
- 决策：新建 `WikiRepository` 作为唯一 wiki 写入口。所有公司/行业/主题页面、index、log、review view 更新只经此入口。单页采用同目录唯一临时文件 + flush/fsync + atomic replace。
- 不采用的方案：继续多入口直接写 Markdown
- 保护的不变量：提交守恒、证据守恒、控制守恒
- 影响范围：所有 wiki 页面、index、log、review queue
- 迁移策略：影子模式验证后替换旧 writer
- 回滚/修订方式：全局 write kill switch 可停止新投影
- 验证：重复投影字节一致；人工注释块被保留
