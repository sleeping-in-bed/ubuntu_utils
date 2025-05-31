import json
from pathlib import Path

from ubuntu_utils.framework.execution_recorder import ExecutionRecorder


def test_execution_recorder(tmp_path: Path):
    record_file = tmp_path / "execution_record.json"
    er = ExecutionRecorder(execution_record_file=record_file)

    def caller():
        result = er._tracer(back_depth=0)
        result = (Path(result[0]).name, *result[1:])
        return result

    trace_result = caller()
    assert trace_result == (
        "test_execution_recorder.py",
        "test_execution_recorder",
        16,
        "    trace_result = caller()\n",
    )

    def caller2() -> bool:
        executed = er.has_executed()
        er.update()
        return executed

    expected_content = {"test_execution_recorder": ["    has_executed = caller2()\n"]}

    has_executed = caller2()
    assert has_executed is False
    assert json.loads(record_file.read_text(encoding="utf-8")) == expected_content

    has_executed = caller2()
    assert has_executed is True
    assert json.loads(record_file.read_text(encoding="utf-8")) == expected_content
