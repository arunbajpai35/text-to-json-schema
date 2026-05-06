import os
from configparser import ConfigParser

ENV_OVERRIDES = {
    ("azure", "api_key"): "AZURE_OPENAI_API_KEY",
    ("azure", "api_base"): "AZURE_OPENAI_ENDPOINT",
    ("azure", "deployment_name"): "AZURE_OPENAI_DEPLOYMENT",
    ("azure", "api_version"): "AZURE_OPENAI_API_VERSION",
}


def load_config(path: str = "config.ini") -> ConfigParser:
    config = ConfigParser()
    config.read(path)
    for (section, key), env_var in ENV_OVERRIDES.items():
        value = os.environ.get(env_var)
        if value:
            if not config.has_section(section):
                config.add_section(section)
            config.set(section, key, value)
    return config
