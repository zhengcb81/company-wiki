from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
TOOLS = ROOT / 'tools/offline_contract_matrix'
(TOOLS / 'runtime.py').write_text((HERE / 'runtime_source.py').read_text(encoding='utf-8'), encoding='utf-8')
p = TOOLS / 'run.py'
s = p.read_text(encoding='utf-8')
s = s.replace('import os\n', '').replace('import subprocess\n', '')
s = s.replace('from report import sha256_file', 'from runtime import Deadline, run_process, synthetic_env\nfrom report import sha256_file')
s = s.replace('_hash_meta(p) for p in self.paths', '_stat_meta(p) for p in self.paths')
s = s.replace('scratch: Path, out_root: Path) -> None:', 'scratch: Path, out_root: Path, deadline: Deadline | None = None) -> None:')
s = s.replace('self.ff_root = ff_root', 'self.batch_deadline = deadline or Deadline()\n        self.deadline = self.batch_deadline\n        self.traces: dict[str, list[dict]] = {}\n        self.ff_root = ff_root')
begin = s.index('        # Inherit the host environment')
end = s.index('\n    def write_state', begin)
s = s[:begin] + '        return synthetic_env(self.scratch, self.cwp_root, self.et_root, with_fmp_key=with_fmp_key)\n\n    def begin_case(self) -> None:\n        self.deadline = self.batch_deadline.case(CASE_TIMEOUT)\n' + s[end:]
begin = s.index('        subprocess.run(', s.index('    def scan'))
end = s.index('\n    # -- FF public CLI', begin)
s = s[:begin] + '''        proc = run_process(
            [sys.executable, "-B", "-m", "company_wiki.source_catalog.cli",
             "--config", str(self.env.wiki / "config/source_catalog.yaml"), "scan"],
            env=self.child_env(), cwd=self.env.wiki, deadline=self.deadline)
        (self.artifacts / "seed-scan.stdout.txt").write_bytes(proc.stdout)
        (self.artifacts / "seed-scan.stderr.txt").write_bytes(proc.stderr)
        if proc.returncode != 0:
            raise RuntimeError(f"CWP seed scan failed ({proc.returncode}): {proc.stderr.decode('utf-8', errors='replace')[:1000]}")
''' + s[end:]
s = s.replace('        proc = subprocess.run(\n            cmd,', '        proc = run_process(\n            cmd,')
s = s.replace('            capture_output=True, env=self.child_env(with_fmp_key=with_fmp_key),\n            cwd=str(self.scratch), timeout=timeout + 20,', '            env=self.child_env(with_fmp_key=with_fmp_key),\n            cwd=self.scratch, deadline=self.deadline.case(timeout),')
s = s.replace('        return {\n            "exit_code": proc.returncode,', '        trace = {\n            "exit_code": proc.returncode,')
s = s.replace('            "stderr_ref": stderr_path.name,\n        }', '            "stderr_ref": stderr_path.name,\n            "request_sha256": sha256_file(req_path),\n            "response_sha256": sha256_file(resp_path),\n        }\n        self.traces.setdefault(case_id, []).append(trace)\n        return trace')
p.write_text(s, encoding='utf-8')
