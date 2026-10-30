# QA cell稳定范围定位：工程验收

不修改原有不可信材料拒绝逻辑。新native parser0.1.2把验证过的cell字符[起,止)放入EvidenceCoordinates；原文cell SHA/切片/fragment SHA必须相同，非NFC或CRLF不能冒签稳定。旧0.1.0/0.1.1坐标、unit ID与回放保持。native range0.1.0→base0.1.1不变，新增range0.1.1→base0.1.2防止版本身份混淆；cache用真实parser与decision依赖分开。

独审发现并修好第二个共因：回放原先不校验来源quality_flags，旧不稳定span可被上层清flag冒签。现在来源标记必须保留，附加保守诊断仍允许；原质量诊断合同不减断言。新增2RED后修复，最终相关6模块160P/17.81秒。前一次广域876P/24.77秒；严格flag相等版本广域877P/1F（1921.26秒）暴露诊断兼容，保留失败且不重跑整批，定向复验160P覆盖该处与全部定位变动。397源mypy与ruff通过，独审最终收据绑定7文件。独审工程通过不等于真实摘要。

真实原件302units/15selected，原guard接受、15/15从原件重新回放、8/8业务输入gold支持，0unstable选中，原件/config未变，0POST/下载，全文仍partial。保存selection与小收据，不复制原PDF、SDK或DB。旧实际real-summary-v2失败0POST/费用证据保留。下一实际run必须新建real-summary-v3，再审模型自然语言与缓存恢复、FF复用和RF实际采用。

施工范围只涉及source/PDF读取与回放及cache依赖；W21三runtime/工区与其他外包目录保持。测试临时目录按owner清理，本轮先前369727202字节已清；母账仍1800368tokens/$0.727945含旧unknown。
