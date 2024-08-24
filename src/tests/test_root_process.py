from src.framework.find_port import *
from src.framework.root_process import *
from src.framework.user_process import *
from __init__ import *


def tests():
    find_port()
    threading.Thread(target=run_user_process, kwargs={'process_name': '1'}).start()
    r: RootProcess = RootProcess(port=get_port())
    r.exec('whoami', no_check=True)
    print(r.capture('echo $DISPLAY', no_check=True))

    r.close_user_process()
    r.close()


if __name__ == '__main__':
    tests()
