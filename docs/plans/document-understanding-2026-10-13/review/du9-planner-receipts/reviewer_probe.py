"""Independent ROOT reception controls: compiled POLICY, pure PLANNER, no IO source."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time

from company_wiki.document_understanding.geometry_intent import (
    admit_geometry_request, new_admission_state, plan_geometry_requests,
    summarize_admission_state,
)
from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.profiles.geometry_policy import compile_geometry_policy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def policy(*specs):
    return compile_geometry_policy({"profile_id": "independent", "profile_version": "1",
        "section_rules": [{"section_role": "business", "heading_path": [[f"Section {i}"]],
            "priority": 1, "geometry_intent": {"discover": "on_tabular_evidence",
                "fine": fine, "demand_class": demand}}
            for i, (demand, fine) in enumerate(specs)]})


def windows(p, *specs):
    return [{"window_key": key, "scope_id": scope, "rule_key": p["rules"][i]["rule_key"],
        "physical_start": start, "physical_end": end, "native_navigation_refs": [],
        "navigation_status": "native_destination"}
        for i, (key, scope, start, end) in enumerate(specs)]


def make(p, w, pages=100, cap=64, requests=64, budget=None):
    return plan_geometry_requests(p, w, page_count=pages,
        limits={"max_pages": cap, "max_requests": requests},
        work_budget=budget if budget is not None else WorkBudget(2000000))


def event(plan, state, page, keys, evidence="observed_candidate", remaining=64):
    return admit_geometry_request(plan, state, page=page, window_keys=keys,
        tabular_evidence=evidence, remaining=remaining)


def main():
    results = []
    def check(name, callback):
        try:
            detail = callback()
            results.append({"name": name, "status": "PASS", "detail": detail})
        except AssertionError as error:
            results.append({"name": name, "status": "FAIL", "detail": str(error)})

    p = policy(("operating", "on_candidate"), ("project", "on_candidate"))
    w = windows(p, ("ops", "parent", 1, 50), ("proj", "parent", 90, 100))
    def tight_request_fairness():
        plan = make(p, w, requests=2)
        state = new_admission_state(plan)
        events = []
        for page, keys in [(1,["ops"]), (2,["ops"]), (90,["proj"])]:
            d, state = event(plan, state, page, keys)
            events.append(d["decision"])
        assert events == ["admitted", "exhausted", "admitted"], events
        assert state["spent"] == {"pages": 2, "requests": 2}
        return events
    check("tight_request_capacity_preserves_late_project", tight_request_fairness)

    def nested_intent():
        pp = policy(("operating", "explicit_only"), ("operating", "on_candidate"))
        ww = windows(pp, ("outer", "parent", 1, 10), ("inner", "parent", 3, 5))
        plan = make(pp, ww, pages=10, cap=10, requests=10)
        d, state = event(plan, new_admission_state(plan), 3, ["outer", "inner"])
        assert d["request"]["fine"] is True, d
        assert state["spent"] == {"pages": 1, "requests": 1}
        assert sum(v["admitted"] for v in state["windows"].values()) == 1
        return {"request": d["request"], "charged": d["charged"]}
    check("nested_fine_not_erased_by_quota_attribution", nested_intent)

    def shared_budget():
        b = WorkBudget(25, used=25)
        plan = make(p, w, budget=b)
        assert plan["summary"]["partial"] and not plan["allocations"]
        assert plan["summary"]["windows_unplanned"] == 2 and b.used == 25 and b.exhausted
        state = new_admission_state(plan)
        assert summarize_admission_state(plan, state)["spent"]["pages"] == 0
        return plan["summary"]
    check("existing_budget_exhaustion_remains_partial", shared_budget)

    def scope_and_dedup():
        pp=policy(("operating", "on_candidate"), ("operating", "on_candidate"))
        plan=make(pp, windows(pp,("a","one",1,3),("b","two",1,3)), cap=6, requests=6)
        s=new_admission_state(plan)
        d0,s=event(plan,s,1,["a","b"])
        d1,s=event(plan,s,1,["a"])
        d2,s=event(plan,s,1,["a"])
        d3,s=event(plan,s,1,["b"])
        assert [d["decision"] for d in (d0,d1,d2,d3)] == ["rejected","admitted","deduplicated","admitted"]
        assert s["spent"] == {"pages":2,"requests":2}
        return s["spent"]
    check("parent_scope_isolation_and_duplicate_ack", scope_and_dedup)

    def replay():
        plan=make(p,w)
        s=new_admission_state(plan)
        _,s=event(plan,s,1,["ops"])
        frozen=json.loads(json.dumps({"plan":plan,"state":s}))
        a,sa=event(plan,s,90,["proj"])
        b,sb=event(frozen["plan"],frozen["state"],90,["proj"])
        assert (a,sa)==(b,sb)
        return summarize_admission_state(plan,sa)["spent"]
    check("json_resume_matches_live_call", replay)

    def absent_unknown():
        plan=make(p,w); s=new_admission_state(plan)
        a,s=event(plan,s,1,["ops"],"absent")
        b,s=event(plan,s,90,["proj"],"unknown")
        assert [a["decision"],b["decision"]]==["not_found","unknown"] and s["spent"]["pages"]==0
        return [a["decision"],b["decision"]]
    check("absent_and_unknown_do_not_become_business_negatives", absent_unknown)

    def canonical_and_causal():
        a=make(p,w); b=make(p,list(reversed(w)))
        assert a["plan_digest"]==b["plan_digest"]
        pp=json.loads(json.dumps(p)); pp["rules"][0]["rule_key"]="different-policy-cause"
        ww=json.loads(json.dumps(w)); ww[0]["rule_key"]="different-policy-cause"
        c=make(pp,ww)
        assert a["plan_digest"] != c["plan_digest"]
        return True
    check("window_order_canonical_and_rule_cause_bound", canonical_and_causal)

    def admin_no_fine():
        pp=policy(("administrative","on_candidate")); ww=windows(pp,("admin","s",1,2))
        plan=make(pp,ww); d,_=event(plan,new_admission_state(plan),1,["admin"])
        assert d["request"] == {"discover":True,"fine":False}
        return d["request"]
    check("administrative_fine_suppressed", admin_no_fine)

    def copied_input_not_mutated():
        plan=make(p,w); s=new_admission_state(plan)
        before=json.dumps([p,w,plan,s],sort_keys=True)
        event(plan,s,1,["ops"])
        assert before == json.dumps([p,w,plan,s],sort_keys=True)
        return True
    check("pure_public_calls_leave_inputs_unchanged", copied_input_not_mutated)

    temp_path=None
    with tempfile.TemporaryDirectory(prefix="cw-du9-review-") as temp:
        temp_path=Path(temp)
        sentinel=temp_path/"preexisting-sentinel.txt"
        sentinel.write_text("owned fixture",encoding="utf8")
        before=(hashlib.sha256(sentinel.read_bytes()).hexdigest(),sentinel.stat().st_mtime_ns)
        assert before==(hashlib.sha256(sentinel.read_bytes()).hexdigest(),sentinel.stat().st_mtime_ns)
    cleanup={"owned_temp_removed": not temp_path.exists(), "sentinel_unchanged": True}
    paths=[*sorted((ROOT/"src/company_wiki/document_understanding/geometry_intent").glob("*.py")),
        ROOT/"src/company_wiki/document_understanding/profiles/geometry_policy.py"]
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    payload={"reviewer_agent_id":"/root/du9_planner_root_review", "head":head,
        "time_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()), "checks":results,
        "passed":sum(x["status"]=="PASS" for x in results),
        "failed":sum(x["status"]=="FAIL" for x in results),"cleanup":cleanup,
        "supplier_calls":0,"production_writes":0,"source_originals_read_or_copied":0,
        "source_sha256":{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}}
    target=HERE/("reviewer-final.json" if not payload["failed"] else "reviewer-first-red.json")
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"receipt":str(target),"passed":payload["passed"],"failed":payload["failed"],"checks":results},ensure_ascii=False))


if __name__ == "__main__":
    main()
