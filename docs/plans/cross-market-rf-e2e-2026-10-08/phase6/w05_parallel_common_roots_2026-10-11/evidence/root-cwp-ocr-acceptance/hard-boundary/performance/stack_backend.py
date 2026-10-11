"""Import-only bounded diagnosis with an independent native stack timer."""

import faulthandler
import os
from measured_backend import event, MeasuredLocalOCRAdapter


class StackImportAdapter(MeasuredLocalOCRAdapter):
    def validate_environment(self):
        trace = open(os.environ["CWP_OCR_PERF_STACK"], "w", encoding="utf-8")
        faulthandler.enable(file=trace, all_threads=True)
        faulthandler.dump_traceback_later(5, file=trace, exit=False)
        event("stack_import_enter")
        try:
            import rapidocr
            event("stack_import_exit", origin=rapidocr.__file__)
        finally:
            faulthandler.cancel_dump_traceback_later()
            trace.close()
