# DU11 阶段 C 真实运行收据摘要（2026-10-18）

完整收据在各自工作区目录（未入 git），这里保存可复核的关键字段；机器可读版本见 `c-live-receipts-20261018.json`。

| 样本 | run_id | status | POST | tokens | 估算费用 | 文档状态 | 错误数 |
|---|---|---|---|---|---|---|---|
| cn-mimo | phaseC-090-fbfd3279d4a0 | PASS | 1 | 15970 | $0.00297 | completed | 0 |
| us-minimax | phaseC-090-93da0ea4fba5 | PASS | 1 | 18093 | $0.00778 | completed | 0 |
| hk-deepseek | phaseC-090-897c0f94fe1c | PASS | 1 | 16813 | $0.00742 | completed | 0 |

- 三次运行均为 `mode=live`、`scope=development regression, not holdout`、原件保护未变、临时库已清理。
- 每次 POST 次数 = 1，均包含 activation recovery 与跨 run 零 POST 检查。
- 香港样本使用 Windows 用户级的有效 `DEEPSEEK_API_KEY` 跑通；早先那条持续返回 401 的密钥不再使用。
- 三家摘要的数字/单位均未发现错误；内容结论见 `review/c-content-review-*.md`。
