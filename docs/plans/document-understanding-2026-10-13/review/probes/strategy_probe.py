"""Read-only policy composition and SEC-form observations; not a production router."""

import importlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(sys.argv[1]).resolve() / "src"))
api = importlib.import_module("company_wiki.document_understanding.profiles")


def observation(form, texts):
    return {"schema_version": "du-input/1",
            "source_ref": {"source_id": "probe", "source_sha256": "passed-through"},
            "metadata": {"form_type": form, "mime_type": "text/html"},
            "coverage": {"native_scan": "complete", "opaque_pages": [], "deferred_pages": []},
            "units": [{"unit_id": f"u{i}", "ordinal": i, "locator": f"l{i}",
                       "page": None, "text": text,
                       "kind": "heading" if i == 0 else "paragraph"}
                      for i, text in enumerate(texts)]}


profiles = {name: api.get_profile(name)["section_priorities"]
            for name in ("prospectus", "offering")}
routes = {}
for form in ("S-1", "F-1", "8-K", "6-K"):
    texts = ([f"FORM {form}", "Registration Statement under the Securities Act of 1933",
              "PROSPECTUS", "Business", "We provide cloud software services.", "Use of Proceeds"]
             if form in ("S-1", "F-1") else
             [f"FORM {form}", "Current report", "Item 2.02 Results of Operations and Financial Condition",
              "Exhibit 99.1", "Second Quarter Results", "Business Highlights",
              "We announced a new product offering."])
    route = api.route_document(observation(form, texts))
    routes[form] = {key: route[key] for key in
                    ("profile_id", "family", "subtype", "confidence", "child_routes")}
print(json.dumps({"profile_sections": profiles, "synthetic_form_routes": routes},
                 ensure_ascii=False, indent=2))
