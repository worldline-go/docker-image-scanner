import os

host = os.environ.get('REGISTRY_SERVER')
user = os.environ.get('REGISTRY_USER')
pwd = os.environ.get('REGISTRY_PASS')

if host is None:
    raise Exception("REGISTRY_SERVER is not defined!")
elif user is None:
    raise Exception("REGISTRY_USER is not defined!")
elif pwd is None:
    raise Exception("REGISTRY_PASS is not defined!")
