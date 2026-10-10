# Versioned original-language transcript fixture

This 66,324-byte TXT is the already downloaded MSFT Q4 FY2026 transcript used by the historical S5 public-search/read end-to-end test. It is an exact byte copy, not a newly fetched or translated document. Original SHA-256: `4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a`.

The fixture removes the implicit adjacent earnings-transcripts checkout dependency, so managed worktrees and CI run the same test. The test copies it into its owned scratch catalog, calls the real three-job and read/search/lookup paths, verifies the SHA, removes the scratch copy, and leaves this committed fixture unchanged. It is an engineering retrieval fixture, not independent acceptance of a company forecast or provider availability. No API key, translation or model output is included.
