import argparse
from framework.root_process import UserProcess
from framework.find_port import get_port


def run_user_process(process_name: str = ''):
    if not process_name:
        parser = argparse.ArgumentParser()
        parser.add_argument('process_name', type=str, help="The name of the process")
        parsed_args = parser.parse_args()
        process_name = parsed_args.process_name

    print('Please input the sudo password in the main process, then press enter in this window to continue.')
    input()
    UserProcess(port=get_port(), process_name=process_name)


if __name__ == '__main__':
    run_user_process()
