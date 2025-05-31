def test1():
    r.exec('sudo pip install --no-cache-dir docker')


def test2():
    r.exec('sudo apt update')
    r.exec('sudo pip install --no-cache-dir docker')
    if some_conditions:
        r.exec('sudo pip install --no-cache-dir docker')
