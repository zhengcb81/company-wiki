# Findings

Suite.setup exported all committed config, inheriting config/local_ocr.json into replay. PPTX default normalization enabled OCR with 30s deadline. Original report retains partial/empty errors only; exact stage/artifact/ledger unavailable after cleanup. Classifier must continue to reject unrelated partial/deadline/refusal. Live export remains explicit current-HEAD snapshot.
