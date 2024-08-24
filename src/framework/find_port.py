import json
from .configs import configs
from .ubuntu_utils_network import find_free_port


def find_port() -> None:
    free_port = find_free_port()
    port_data = json.dumps(free_port)
    configs.port_file.write_text(port_data, encoding='utf-8')
    print(f'Running on port: {free_port}')


def get_port() -> int:
    port_data = configs.port_file.read_text(encoding='utf-8')
    return json.loads(port_data)


if __name__ == '__main__':
    find_port()
