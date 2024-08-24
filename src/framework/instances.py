from .root_process import *
from .find_port import *

find_port()
r: RootProcess = RootProcess(port=get_port())
remote: Remote = Remote()


def close_all():
    r.close_user_process()
    r.close()
