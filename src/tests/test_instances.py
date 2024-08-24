from src.framework.instances import *


def test():
    er = ExecutionRecorder()
    filename, function_name, line_number, code_text = er._tracer(back_depth=-1)
    print(f'{filename}, {function_name}, {line_number}, {code_text}')

    print(r.vars)
    r.exec('echo 1')
    ret = r.capture('echo 2')
    print(f'return: {ret.stdout}')
    ret = r.capture('echo 2')
    print(f'return: {ret.stdout}')
    er._execution_record_file.unlink()

    c = Check()
    c.commands_path = Path(__file__)
    try:
        rp = RootProcess(_check=c)
    except Check.DuplicateCodeError as e:
        pass
    else:
        raise AssertionError
    close_all()
    print()


if __name__ == '__main__':
    test()
