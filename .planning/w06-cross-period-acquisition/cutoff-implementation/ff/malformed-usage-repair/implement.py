"""Use the one validated receipt snapshot for every post-receipt ET failure."""
import hashlib
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
FREEZE = HERE.parents[1] / 'product-freeze.json'
freeze = json.loads(FREEZE.read_text(encoding='utf-8'))
TREE = Path(freeze['roots']['ff'])
path = TREE / 'scripts/transcript_tool_transport.py'
expected = next(item['sha256'] for item in freeze['files'] if item['repository'] == 'ff' and item['path'] == 'scripts/transcript_tool_transport.py')
if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
    raise RuntimeError('Unexpected production drift')
text = path.read_text(encoding='utf-8')
start_marker = '        self._last_provider_usage = _provider_usage(usage_stderr, request["request_id"], credential)\n'
start = text.index(start_marker, text.index('    def _et_result('))
end = text.index('        return result\n', start) + len('        return result\n')
text = text[:start] + '''        # Transport usage is independent of whether stdout is a valid document.
        # Parse the bounded, request-bound receipt once and preserve that snapshot
        # in all later failure projections, including malformed JSON/type errors.
        provider_usage = _provider_usage(usage_stderr, request["request_id"], credential)
        self._last_provider_usage = provider_usage

        def unavailable(
            reason: str, *, calls: int = 1, retryable: bool = False,
        ) -> dict[str, Any]:
            return {
                "status": "provider_unavailable",
                "reason": reason,
                "retryable": retryable,
                "provider_calls": calls,
                "provider_started": self._provider_started(provider_usage),
                **provider_usage,
            }

        if _credential_exposed(stdout, usage_stderr, credential):
            return unavailable("provider_credentials_leaked")
        try:
            result = json.loads(stdout.decode("utf-8", errors="strict"))
        except (UnicodeError, json.JSONDecodeError):
            return unavailable("provider_result_invalid")
        if not isinstance(result, dict):
            return unavailable("provider_result_invalid")
        if result.get("status") == "not_found":
            # Bind this one process receipt to the current request. This is not
            # another company-identity lookup or a source-byte validation.
            invalid = (
                result.get("schema_version") not in (
                    "earnings-transcript-result/1", "earnings-transcript-result/2",
                )
                or result.get("request_id") != et_request["request_id"]
                or result.get("provider") != et_request["provider"]
                or result.get("fiscal_period")
                != f"{et_request['fiscal_year']}-Q{et_request['fiscal_quarter']}"
                or type(result.get("candidate_count")) is not int
                or result["candidate_count"] != 0
            )
            if code != 0 or invalid:
                return unavailable(
                    "provider_tool_failed" if code != 0 else "provider_result_invalid",
                )
            # A completed lookup with no eligible transcript is not a provider
            # outage. Only a producer-declared finite date diagnostic can name
            # a cutoff; neither zero candidates nor child free text proves one.
            diagnostic = result.get("error_code")
            reason = (diagnostic if isinstance(diagnostic, str)
                      and diagnostic in ET_NOT_FOUND_DIAGNOSTICS else "exact_transcript_missing")
            return {
                "status": "not_found",
                "reason": reason,
                "retryable": False,
                "provider_calls": 1,
                "provider_started": self._provider_started(provider_usage),
                **provider_usage,
            }
        if result.get("status") != "fetched":
            error_code = result.get("error_code")
            safe_code = (
                error_code
                if isinstance(error_code, str) and error_code in _KNOWN_ET_ERRORS
                else "provider_unavailable"
            )
            calls = 0 if safe_code in {"provider_credentials_missing", "provider_disabled", "provider_cost_unknown", "provider_cost_budget_exceeded", "candidate_discovery_unavailable", "candidate_fetch_unavailable", "unsupported_market", "unsupported_exchange", "provider_credentials_file_unavailable", "provider_credentials_file_empty", "provider_credentials_file_invalid"} else 1
            return unavailable(
                safe_code, calls=calls,
                retryable=provider_usage["provider_usage_complete"] and result.get("status")
                in ("rate_limited", "provider_error"),
            )
        if code != 0:
            return unavailable("provider_tool_failed")
        return result
''' + text[end:]
path.write_text(text, encoding='utf-8', newline='\n')
with (TREE / '.planning/w06-cutoff-result/progress.md').open('a', encoding='utf-8') as stream:
    stream.write('\nE正规RED：3FAIL/75deselected/0.37s，三个实际_et_result错误输出把requests1清成None，非import异常。已实施局部共享unavailable投影：一次已验stderr usage快照；JSON/非dict/泄key/错误notfound/已调用失败/非零exit均共享，正文不合法不覆写用量，未知/污染receipt仍未知。待一次集中责任节点。\n')
print(json.dumps({'product_files_changed': 1, 'et_changed': False, 'post_receipt_usage_parse_count': 1, 'shared_failure_projection': True}))
