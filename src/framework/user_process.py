import time
import argparse
from .root_process import UserProcess
from .find_port import get_port


def run_user_process(process_name: str = ''):
    if not process_name:
        parser = argparse.ArgumentParser()
        parser.add_argument('process_name', type=str, help="The number of the process")
        parsed_args = parser.parse_args()
        process_name = parsed_args.process_name

    time.sleep(0.5)
    UserProcess(port=get_port(), process_name=process_name)


if __name__ == '__main__':
    run_user_process()
