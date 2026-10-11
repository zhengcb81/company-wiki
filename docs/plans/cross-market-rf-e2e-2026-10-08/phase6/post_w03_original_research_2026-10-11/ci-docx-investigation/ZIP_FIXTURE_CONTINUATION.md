# CI ZIP fixture 跨平台责任补齐

## 证据与假设

精确新source CI38105648234只有DOCX两项legacy fingerprint失败，本地全3196通过。完整远端旧record fingerprint63c83b5638f54e4454dd66e69fbd51b89cd5b69f8f2f9a1146298e87c64e7c97，原Windows历史a6580fca5dcd6c063e2447bf5cf489aaabd8f61c52856646db744cb68d0031e4。调查ZIP create_system及其他封套元数据是否使source SHA不同；绝不能换expected为本次actual或排掉source/identity字段。

## 单一责任write set

ROOT只改 tests/unit/test_docx_heading_normalization.py fixture/package及其跨宿主反例；当前7产品源码/default版本/旧1.0 parser逻辑不改。其他审查员仅roles各自报告，不互读初稿。

## 先验测试与实施

1. 保存远端日志和本地host-default0/3实际fixture SHA、完整record fingerprint对照，要求重现远端63c83值；不改生产config/原件。
2. 写宿主默认ZipInfo system0和3的参数化反例，fixture最终原件仍必须为旧六单元d428ad041147fb650671ee805c38a03539b4f28529a5516bce325cc3a8541761，完整1.0 record仍a6580fca…，原metadata/sourceID/locator/replay全部断言不减，先RED。
3. 仅确定测试封套元数据，所有平台生成同一原字节；集中DOCX+fixture相关GREEN。不能写product按platform分支、不能whitelist hash跳验、不能修改旧证据。
4. 一个独立定点审查核远端相同失败已复现、旧断言保持、正负控；正常commit/ff/push、新精确CI。既有public1.0/1.1大节点未受产品源码变化不重复，普通hooks照常。

## 验收与恢复

业务源SHA、配置SHA、sealed三运行保持；原日志/RED/新GREEN全部保留。不存在新增供应商调用/费用/下载。实际Linux CI为最后宿主证据，不能用Windows PASS代签。

实际双宿主probe精确复现远端63c83b56，Windows d428ad04 / Linux 1af5cb9e，各2729B、6正文与locator相同。先前c29c是独立最小标题原件，不能当六单元历史fixture；已按实际字节纠正施工卡，本身未改任何证据。
