> 最终覆盖：首轮15已删/9hold为历史过程；root按同一精确清单用原生Force清除只读夹具，9根也已删除。24根合计14,543,053B，无剩余hold/ACL改动；见[最终收尾](gd_storage_final_cleanup_2026-10-03.md)及补批JSON。下方保留首轮真实结果。

# B4补批测试临时目录清理收据（2026-10-03）

冻结卡：gd_b4_test_scratch_cleanup_2026-10-03.md；SHA-256 ebfcaf694cd9b076bd9700f2deaf59697df665028a1aa3bd11874c75b6d3d65c。

移除 **15/24 根**，hold 9 根；已验证新释放 **259795 B**（0.000241953 GiB）。

创建账号 use_default 逐根完整递归读取（ErrorAction Stop），复核 exact根/祖先/子树无reparse、文件数/字节与冻结卡相同，再原生PowerShell Remove-Item -LiteralPath -Recurse。没有改ACL、没有Git操作，没有清理其他目录。

owner sandbox 禁止WMI查询，初次因此没有删除。正常用户只读WMI查询确认24个唯一根名0项命中后，全部删除操作仍在创建账号中完成。

主库size/mtime、配置hash/mtime、Worker控制hash/mtime和三资料根有限统计前后相同：True；Worker仍 paused。

| 精确根名 | 已读字节 | 已读文件 | 完整读取 | 结果 | 新释放B | 删除后存在 |
|---|---:|---:|---|---|---:|---|
| .rf-ca301-safe-20261003 | 0 | 0 | True | deleted | 0 | False |
| .rf-ca301-suite-20261003 | 17 | 1 | True | deleted | 17 | False |
| .rf-ca301-suite-20261003b | 16 | 1 | True | deleted | 16 | False |
| .rf-ci-first-failure-20261003 | 51223 | 30 | True | hold | 0 | True |
| .rf-ci-first-safe-20261003 | 51223 | 30 | True | hold | 0 | True |
| .rf-ci-focused-temp-20261003 | 3798 | 1 | True | hold | 0 | True |
| .rf-ci-focused-temp-20261003b | 3798 | 1 | True | hold | 0 | True |
| .rf-ci-rest-base-20261003 | 1652338 | 296 | True | hold | 0 | True |
| .rf-ci-rootcause-base-20261003 | 3124071 | 117 | True | hold | 0 | True |
| .rf-ci-rootcause-base2-20261003 | 3474375 | 137 | True | hold | 0 | True |
| .rf-ci-second-firstfail-20261003 | 1912849 | 60 | True | hold | 0 | True |
| .rf-ci-suite-final-20261003 | 4009583 | 310 | True | hold | 0 | True |
| .rf-ci-tail-base-20261003 | 258048 | 1 | True | deleted | 258048 | False |
| .rf-compat-tests-base-20261003 | 16 | 1 | True | deleted | 16 | False |
| .rf-fc1102-current-wiki-20261003 | 0 | 0 | True | deleted | 0 | False |
| .rf-fc1102-temp-20261003 | 0 | 0 | True | deleted | 0 | False |
| .rf-fc1307-tmp-20261003 | 0 | 0 | True | deleted | 0 | False |
| .rf-meta-tests-20261003 | 0 | 0 | True | deleted | 0 | False |
| .rf-prepush-tmp-20261003c | 0 | 0 | True | deleted | 0 | False |
| .rf-source-reader-guard-20261003 | 0 | 0 | True | deleted | 0 | False |
| .rf-source-reader-guard-20261003b | 0 | 0 | True | deleted | 0 | False |
| .rf-zr1102-collect-20261003 | 0 | 0 | True | deleted | 0 | False |
| .tmp-pytest-narrative-cap | 849 | 1 | True | deleted | 849 | False |
| .tmp-pytest-narrative-g1 | 849 | 1 | True | deleted | 849 | False |

## 限制及保留项

- .rf-ci-first-failure-20261003：You do not have sufficient access rights to perform this operation or the item is hidden, system, or read only.
- .rf-ci-first-safe-20261003：You do not have sufficient access rights to perform this operation or the item is hidden, system, or read only.
- .rf-ci-focused-temp-20261003：You do not have sufficient access rights to perform this operation or the item is hidden, system, or read only.
- .rf-ci-focused-temp-20261003b：You do not have sufficient access rights to perform this operation or the item is hidden, system, or read only.
- .rf-ci-rest-base-20261003：You do not have sufficient access rights to perform this operation or the item is hidden, system, or read only.
- .rf-ci-rootcause-base-20261003：You do not have sufficient access rights to perform this operation or the item is hidden, system, or read only.
- .rf-ci-rootcause-base2-20261003：You do not have sufficient access rights to perform this operation or the item is hidden, system, or read only.
- .rf-ci-second-firstfail-20261003：You do not have sufficient access rights to perform this operation or the item is hidden, system, or read only.
- .rf-ci-suite-final-20261003：You do not have sufficient access rights to perform this operation or the item is hidden, system, or read only.

历史样本PDF均为fake或fitz生成夹具；未删除真实下载原件。进程检查仅针对可见commandline中的唯一根名，不能证明所有open handle不存在。

磁盘可用空间观察增量 172032 B，与逻辑字节按不同口径记录；观察在写收据前。
