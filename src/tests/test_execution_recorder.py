from src.framework.execution_recorder import *
from __init__ import *
import json


def tests():
    execution_record_file = tmp_dir / 'exec.json'
    er = ExecutionRecorder(execution_record_file=execution_record_file)

    def caller():
        result = er._tracer(back_depth=0)
        result = (Path(result[0]).name, *result[1:])
        assert result == ('test_execution_recorder.py', 'tests', 15, '    caller()\n'), result

    caller()

    def caller() -> bool:
        executed = er.has_executed()
        er.update()
        return executed

    execution_record_file_content = {'tests': ['    has_executed = caller()\n']}
    has_executed = caller()
    assert has_executed is False
    assert json.loads(execution_record_file.read_text(encoding='utf-8')) == execution_record_file_content
    has_executed = caller()
    assert has_executed is True
    assert json.loads(execution_record_file.read_text(encoding='utf-8')) == execution_record_file_content

    execution_record_file.unlink()


if __name__ == '__main__':
    tests()
