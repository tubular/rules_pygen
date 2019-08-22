from coolname import generate


def get_funny_name():
    return ''.join(x.capitalize() for x in generate())
