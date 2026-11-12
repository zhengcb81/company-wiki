"""Scratch probe: which third-party SDKs do the CLI import closures need?"""
import sys

sys.path.insert(0, r"C:\Users\郑曾波\Projects\mb11-cwp\src")

OPTIONAL = {"pymupdf", "fitz", "docx", "pptx", "openpyxl", "xlrd", "opencc",
            "bs4", "markdownify", "langid", "docling", "cryptography", "playwright"}


class RefuseRuntime:
    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".")[0]
        if root in OPTIONAL:
            raise AssertionError("optional sdk imported: " + fullname)
        return None


sys.meta_path.insert(0, RefuseRuntime())

TARGETS = [
    "company_wiki.source_contract.cli",
    "company_wiki.source_catalog.announcement_cli",
    "company_wiki.source_catalog.cli",
    "company_wiki.source_catalog.source_reader_cli",
    "company_wiki.source_catalog.source_query_cli",
    "company_wiki.source_catalog.company_source_index_cli",
    "company_wiki.source_catalog.source_export_v2_cli",
    "company_wiki.source_catalog.identity_cli",
    "company_wiki.source_catalog.transcript_import_cli",
    "company_wiki.automation.narrative_transport_cli",
    "company_wiki.automation.narrative_batch_cli",
    "company_wiki.source_catalog.processed_document_cli",
    "company_wiki.source_catalog.financial_statements.cli",
]

import importlib

third_party = set()
stdlib = set(sys.stdlib_module_names)
for target in TARGETS:
    before = set(sys.modules)
    try:
        importlib.import_module(target)
    except AssertionError as refusal:
        print("%-55s REFUSED %s" % (target, refusal))
        continue
    for name in set(sys.modules) - before:
        root = name.split(".")[0]
        if root not in stdlib and root != "company_wiki":
            third_party.add(root)
    print("%-55s ok" % target)
print("third-party modules in the closures:", sorted(third_party))
