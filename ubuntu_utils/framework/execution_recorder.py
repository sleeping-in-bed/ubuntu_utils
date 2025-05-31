import inspect
from collections import defaultdict
from pathlib import Path

from .lib.serialization_utils import Serializer
from .utils import warning_print


class ExecutionRecorder:
    def __init__(self, execution_record_file: str | Path):
        self._s = Serializer(path=execution_record_file, data_type=dict)
        self._execution_record = defaultdict(list, self._s.load_json())

    @staticmethod
    def _tracer(back_depth: int = 0) -> tuple[str, str, int, str]:
        """
        Get the function's frame that called this function,
        for example, a function named 'caller', called this function:
            def caller():
                _tracer() # this line in the "caller.py" file's 10th line
            caller() # this line in the "caller.py" file's 11th line
        will return:
            ('caller.py', 'caller', 11, 'caller() # this line in the "caller.py" file's 11th line')

        :param back_depth: equals '2 + back_depth'
        :return: the (filename, func_name, lineno, code) tuple
        """
        back_depth = 2 + back_depth
        current_frame = inspect.currentframe()
        for _ in range(back_depth):
            current_frame = current_frame.f_back
        frame_info = inspect.getframeinfo(current_frame)

        return (
            frame_info.filename,
            frame_info.function,
            frame_info.lineno,
            frame_info.code_context[0],
        )

    def has_executed(self, back_depth: int = 0) -> bool:
        filename, function_name, line_number, code_text = self._tracer(
            back_depth=1 + back_depth
        )
        if code_text in self._execution_record[function_name]:
            warning_print(
                f'Context: "{filename}, {function_name}, {line_number}, {code_text.strip()}" executed'
            )
            return True
        return False

    def update(self, back_depth: int = 0) -> None:
        filename, function_name, line_number, code_text = self._tracer(
            back_depth=1 + back_depth
        )
        func_exec_record = self._execution_record[function_name]
        if code_text not in func_exec_record:
            func_exec_record.append(code_text)
        self._s.dump_json(self._execution_record, minimum=False)
