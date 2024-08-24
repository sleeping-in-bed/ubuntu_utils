import inspect
import json
from collections import defaultdict
from pathlib import Path
from .utils import load_dict, warning_print


class ExecutionRecorder:
    def __init__(self, execution_record_file: str | Path):
        self._execution_record_file = execution_record_file
        self._execution_record = load_dict(self._execution_record_file)
        self._execution_record = defaultdict(list, self._execution_record)

    @staticmethod
    def _tracer(back_depth: int = 0) -> tuple[str, str, int, str]:
        """
        return the (filename, func_name, lineno, code) tuple
        return the function's frame that called the function,
        for example, a function named 'caller', called this function '_tracer', will return
        (which file called 'caller', which function called 'caller',
        the lineno of 'caller' being called,  the code of 'caller' being called)
        """
        back_depth = 2 + back_depth
        current_frame = inspect.currentframe()
        for _ in range(back_depth):
            current_frame = current_frame.f_back
        frame_info = inspect.getframeinfo(current_frame)
        filename = frame_info.filename
        function_name = frame_info.function
        line_number = frame_info.lineno
        code_text = frame_info.code_context[0]
        return filename, function_name, line_number, code_text

    def has_executed(self, back_depth: int = 0) -> bool:
        filename, function_name, line_number, code_text = self._tracer(back_depth=1 + back_depth)
        if code_text in self._execution_record[function_name]:
            warning_print(f'Context: "{filename}, {function_name}, {line_number}, {code_text.strip()}" executed')
            return True
        return False

    def update(self, back_depth: int = 0) -> None:
        filename, function_name, line_number, code_text = self._tracer(back_depth=1 + back_depth)
        func_exec_record = self._execution_record[function_name]
        if code_text not in func_exec_record:
            func_exec_record.append(code_text)
        self._execution_record_file.write_text(json.dumps(self._execution_record, ensure_ascii=False, indent=4))
