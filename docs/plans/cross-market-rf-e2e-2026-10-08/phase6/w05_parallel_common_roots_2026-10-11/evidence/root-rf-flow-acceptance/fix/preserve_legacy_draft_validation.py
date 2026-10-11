from pathlib import Path
path = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root/scripts/contracts/document.py')
body = path.read_text(encoding='utf-8')
old = '''    for segment in data["segments"]:
        validate_recognition_metadata(segment, source_index, claim_index)
'''
new = '''    # Legacy structural/draft validation accepts an omitted recognition
    # contract; the forecast execution layer still requires it. Once authors
    # supply metadata, validate its structure before any DAG dependency walker
    # indexes timing-specific fields. Do not invent carry-in defaults.
    for segment in data["segments"]:
        if "recognition" in segment:
            validate_recognition_metadata(segment, source_index, claim_index)
'''
assert old in body
path.write_text(body.replace(old, new), encoding='utf-8')
print('Preserved old omitted-recognition structural validation; present invalid contracts still reject before DAG traversal')
