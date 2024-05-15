from . import *

r: RootProcess = RootProcess(routing_key=user_mark, binding_key=user_result_mark)
remote: Remote = Remote()


def close_all():
    r.close_user_process()
    r.close()
