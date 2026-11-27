# Isolated T3 acquisition assurance

Company-wiki owns the temporary catalog, original files, identity snapshot, provider state and acquisition evidence for this probe. Filing-fetch owns the run and case selection, request limits and final T3 receipt. The control command accepts the `cwp-t3-workspace-request/1` JSON wire contract over standard input and emits `cwp-t3-workspace/1` on standard output.

## Deployment

Use the interpreter that runs the released company-wiki package. On Windows the configured interpreter should be headless. In the existing Filing-fetch deployment JSON, add the command array as `connection.commands.t3_workspace` and retain every existing operation binding.

```json
[
  "<absolute CWP interpreter>",
  "-B",
  "-m",
  "company_wiki.source_catalog.t3_workspace_cli",
  "--workspace-root", "<short absolute dedicated scratch directory>",
  "--owner-root", "<absolute released CWP project directory>",
  "--acquisition-config", "<absolute current CWP provider configuration file>",
  "--identity-cache", "<absolute current CWP security-master snapshot directory>"
]
```

The owner root expands the existing provider configuration. Each case writes a fresh catalog and copies the selected market's identity snapshot. Adapter code paths still resolve to their configured checkout. Catalog staging, raw-only Dayu provider state and CWP diagnostics are scoped to the case directory. The configured provider adapters must implement the same native finite acquisition budgets as the existing live path.

`open` prepares or returns the workspace bound to the supplied run and case. There is no retrieval during workspace setup. `observe` takes current catalog and byte evidence after the original operation. The `first` and `reused` observations carry source ID, digest and mtime. The `corrupt` observation comes from an isolated, deliberately corrupted fixture. `close` seals the original binding and removes its directory. The seal and lock are small records owned by the configured scratch directory. The interrupted case can be recovered or explicitly closed with the original run and case ID, including when the open reply was lost.

The control command never starts the Filing-fetch T3 job. The existing explicit `run-live` entrypoint is responsible for starting it. The original Filing-fetch receipt remains available through `get` even after workspace cleanup.
