import os


def read_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError
    
    with open(file_path, mode="r") as f:
        txt = f.read()

    return txt


def read(path):
    # TODO: check if its html url, download it
    return read_file(path)