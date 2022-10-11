import os


def read_token(p):
    with open(p) as f:
        token = f.readline()
    return token

