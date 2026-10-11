# W06-CWP-PORTABILITY ROOT 工具层系统修复

## 当前交付

作者阶段 READY_FOR_INDEPENDENT_REVIEW，未自行commit、并主线、安装或改CI。
ROOT树基线8862372f714209cff1b218d77b5c4b8af6bc74dc，worker merge f8d5e0f4 pending。
只写 tools/source_root_portability、本卡两个新测试、自己PWF/handoff；生产src/scripts/
config、旧生产测试、真实raw均未修改。

## 共因修复

1. 目录名不等于归属：唯一创建child+created_dirs，初始化失败/最终仅清自建项；
   无ownership对象的legacy cleanup不删任何文件。容器只作浅stat inventory，
   不rglob/hash用户湖。旧cleanup正控改为实际归属API，保留sentinel字节/SHA/
   旧文件仍在断言，新增六类既有目录及空目录保护。
2. 原CLI stdout/exit/stderr/bundle/manifests留证，移除Reader facts伪造manifests。
   derived observations与原wire分开；格式错误如实记录，不补成功。
3. typed oracle要求S1-S7完整、每原件ref迁移/最终恢复、新版本真打开、
   verify_version不冒充bytes、真实wire引用/固定期次/实际根映射/无路径。
   非法嵌套形状结构化INVALID_RECORD；PARTIAL/UNKNOWN保留。
4. consumer直接open完整SourceRef；错size/MIME/schema真实拒绝，不用query_ref替换pin。
5. 平台env allowlist，synthetic HOME/TEMP、禁dotenv，child导入生产模块前启用离线/
   凭证文件guard。无新许可文件、权限分类、人工签收或小节点门。

## 测试与真实回放

- 正式初始RED：10 FAIL+1合法根迁移正控，3.95s；副本ref覆盖另1 RED，0.44s。
  旧intake/worker FAIL保留。中途合法wire夹具doc_key查找错误也留存，不归生产bug；
  改夹具符合实际wire，不改业务断言适应故障。
- 最终冻结节点：56 PASS/1 SKIP/1 warning，10.97s，ruff PASS。
  SKIP为Windows无权创建symlink；runtime lstat/reparse拒绝逻辑未移除。
  warning仅disabled plugin autoload后既有asyncio_mode未识别，不是测试失败。
- 当前ROOT生产Reader实际CLI七场景PASS 4.755s；3 distinct来源、4 doc_key。
  S2/S6四ref别名均实际读取/描述。TXT-copy共享ref，不因此称为四physical path实读；
  S4真删除主副本并读回备用副本。
- 58 in-process Reader API calls+4 child read/export invocations=62 API calls，
  含元数据查询/预期拒绝，不是62次成功bytes读取。
- 7已有文件SHA、7既有空目录保留；唯一owned child absent，整临时根restored absent。
  产品与8生产模块前后SHA相同，加载本ROOT src。
- 实际network/provider/LLM调用/费用为0。guard记录一个blocked socket操作；
  1.165s synthetic初始化诊断明确为socket.bind（socket.__new__允许），bind被拒绝；
  无connect/DNS事件，不隐去该观测，不推断为生产层bug。

## 冻结接口与下一步

中央fix/final-refresh/final-node.json、real-run-report.json为最终；
此前fix/final-node.json为55 PASS历史，不能覆盖成最终。
见fix/product-freeze.json和manifest.json；旧intake字节原样保留。
非作者重放反例/正控与冻结证据，不重复生产全集；ROOT负责最终签收和正常
commit/master/push。冻结后作者停止写入。范围仅Windows synthetic Reader/catalog/
CLI/工具层，不能扩大为真实云、Dayu/Dropbox、OCR、LLM、投资质量或POSIX认证。
