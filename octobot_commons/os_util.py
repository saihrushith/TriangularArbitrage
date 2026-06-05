import os

def parse_boolean_environment_var(key, default="False"):
    val = os.environ.get(key, default).lower()
    return val in ["true", "1", "yes", "y"]
