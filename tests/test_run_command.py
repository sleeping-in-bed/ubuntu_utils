from framework.run_command import *


def test():
    er = ExecutionRecorder()
    filename, function_name, line_number, code_text = er._tracer(back_depth=1)
    print(f'{filename}, {function_name}, {line_number}, {code_text}')

    r.exec('echo 1')
    ret = r.capture('echo 2')
    print(f'return: {ret}')
    ret = r.capture('echo 2')
    print(f'return: {ret}')
    er.execution_record_file.unlink()

    c = Check()
    c.commands_path = Path(__file__)
    try:
        run = Run(_check=c)
    except DuplicateCodeError as e:
        pass
    else:
        raise AssertionError


if __name__ == '__main__':
    test()
