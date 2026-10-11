from pathlib import Path
FF=Path(r'C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
p=FF/'tests/test_w06_case_authority.py';text=p.read_text(encoding='utf-8')
text+='''
@pytest.mark.parametrize("cid",[c["id"] for c in frozen_report()["cases"]])
def test_authority_original_all_case_contracts_and_request_vectors_match(cid):
    from case_specs import get_spec
    c=case(frozen_report(),cid);spec=get_spec(cid)
    assert spec.metadata_errors(c)==[]
    for index,run in enumerate(c["actual"]["runs"]):
        request=json.loads((FIXTURE/"artifacts"/run["request_ref"]).read_text(encoding="utf-8"))
        assert spec.request_errors(index,request)==[]

def test_authority_runner_registry_consumes_same_fixed_objects():
    from cli_main import _case_registry
    from case_specs import case_specs
    rows=_case_registry()
    assert tuple(cid for cid,_ in rows)==tuple(spec.id for spec in case_specs())
    assert all(runner.__self__ is spec for (_,runner),spec in zip(rows,case_specs()))

def test_authority_runner_rejects_drift_before_process_and_binds_valid_input(tmp_path):
    from case_specs import get_spec
    from run import Context
    from subprocess import CompletedProcess
    from unittest.mock import patch
    ctx=Context(ff_root=tmp_path/"ff",cwp_root=tmp_path/"cwp",et_root=tmp_path/"et",scratch=tmp_path/"scratch",out_root=tmp_path/"output")
    spec=get_spec("fin_cn_annual_hit")
    bad=spec.runs[0].request();bad["market"]="HK"
    with patch("run.run_process") as launch:
        with pytest.raises(ValueError,match="contract drift"):
            ctx.run_ff(bad,case_id=spec.id)
        launch.assert_not_called()
        launch.return_value=CompletedProcess([],0,b'{"status":"synthetic-control-only"}',b'')
        trace=ctx.run_ff(spec.runs[0].request(),case_id=spec.id)
        assert json.loads(launch.call_args.kwargs["input"])==spec.runs[0].request()
        path=ctx.artifacts/trace["fixture_ref"]
        assert hashlib.sha256(path.read_bytes()).hexdigest()==trace["fixture_sha256"]
    ctx.active_case_spec=get_spec("call_past_cutoff")
    with patch("run.run_process") as launch:
        with pytest.raises(ValueError,match="active case"):
            ctx.run_ff(spec.runs[0].request(),case_id=spec.id)
        launch.assert_not_called()

def test_authority_runner_rejects_wrong_fixture_before_launch(tmp_path):
    from case_specs import get_spec
    from run import Context
    from unittest.mock import patch
    ctx=Context(ff_root=tmp_path/"ff",cwp_root=tmp_path/"cwp",et_root=tmp_path/"et",scratch=tmp_path/"scratch",out_root=tmp_path/"output")
    spec=get_spec("call_past_cutoff")
    ctx.write_state(scenario="success",calls_file=ctx.env.calls_file(spec.id),call_date="2025-06-01",receipt_tag=spec.id)
    with patch("run.run_process") as launch:
        with pytest.raises(ValueError,match="fixture"):
            ctx.run_ff(spec.runs[0].request(),case_id=spec.id)
        launch.assert_not_called()
'''
p.write_text(text,encoding='utf-8')
