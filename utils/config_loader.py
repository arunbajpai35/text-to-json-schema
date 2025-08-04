from configparser import ConfigParser

def load_config():
    config = ConfigParser()
    config.read("config.ini")
    return config
