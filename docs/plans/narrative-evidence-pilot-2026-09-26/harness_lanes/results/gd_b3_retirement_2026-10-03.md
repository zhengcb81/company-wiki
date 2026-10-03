# G-D B3：实际删除与空间收尾

## 发布与节点

B3工具/合同发布`6ab25373`，65项不同节点检查全绿。首次CI发现既有AUTO初始化mixed snapshot竞态；确定性RED后修3行readonly BEGIN，Win/Ubuntu各32项通过，保留M14/坏库拒绝。修复`d61b8f645bf871c0feb3834d7fba4f2b91fd496a`正常推送；[Actions37122264065](https://github.com/zhengcb81/company-wiki/actions/runs/37122264065)成功，57秒。没有完整恢复备份、全仓coverage或live FMP请求。

## 实际apply

使用同一metadata audit和已发布CLI，39.728秒，status=removed，reconciled=false；两候选均缺席：

| 精确派生文件 | 实际删除B |
|---|---:|
| `.source_catalog/retirement/20260926T170825Z-4a9c67e1/catalog.full.sqlite3.zst` | 6,198,704,362 |
| `source_manifests/archive/2026-08-07/retired-evidence.jsonl.gz` | 5,207,478,767 |
| 合计 | **11,406,183,129 /10.622836GiB** |

原始文档不在操作清单。current catalog完整SHA仍`30794a01e04a9e77ec13cd7b27a3f24bf9861bda9fc7c3c50a2b362830fbc823`，size=3,055,800,320B、mtime_ns=1790490231504738600。前后完整SHA/size/mtime由工具实读核验，来源/版本/位置事实不变。保留metadata audit、prepared/retired、B1和新intent/receipt；旧派生span正文不再保证full restore，查询明确不可用且source identity保留。

durable收据位置：`.source_catalog/archive-cleanup/36058098a1755efc3229bf02/receipt.json`。可提交的[本次执行记录](gd_b3_production_apply_2026-10-03.json)包含完整绑定/字节/状态。

同卷free观测127,238,299,648→138,599,047,168B，增加11,360,747,520B；与逻辑删除分列，其他进程变化不强归因。生产重复apply：replayed=true/newly_deleted_bytes=0。B1已完成历史收据在archive缺席后仍回显removed，历史3,055,796,224B不重计新收益。

## 最新实际空间

[fresh machine inventory](gd_storage_post_cleanup_2026-10-03.json)不跟随reparse：

- 三资料根 **31,286,231,649B /29.137574GiB**，公司资料目录25,198,502,813B与之前总字节数相等，本次实读33,133文件；三根访问错误/reparse均0。不会写成“全库原文重新hash”；本批只有归档/主库字节验证，原文不在操作清单。
- 主仓可读32,478,532,846B，剩余登记worktree342,640,392B，共**32,821,173,238B /32.821十进制GB /30.567GiB**。全主仓24个历史ACL测试目录仍不可读，故全仓为可读下界；不以此宣称旧临时目录全部清掉。
- 本轮B3+B4首批23根+补批4根逻辑释放 **13,049,081,047B /12.152904GiB**。同口径原45.87十进制GB没有重新增长，而是留下两旧派生archive/历史checkout；此前B1和37.630GiB旧库净收益不再计入本轮。
- 7个Git登记含main、3个managed根、RF pinned根及两个近空.git根。managed附件UI显示archived但物理路径仍存在，269,497,387B未计释放，不能普通Git移除代替managed生命周期。两历史review refs已推远端；四报告main持久同blob保留，无重复副本。

## 下一步

Phase61本轮归档/普通工作树收尾完成。生产Worker仍paused；按[N4细则](../../n4_production_batch_implementation.md)先scope/持久预算，再真实model/composition/终态小收据，最后B2切换旧normalized调用者后清理derived/index。N4尚未实现，不能将这次空间处置冒充生产全量叙述处理完成。
