from io import StringIO

from ruamel.yaml import YAML


def reyamlify(value: str) -> str:
    """Convert value to yaml object and dump it again.

    recipy.to_yaml() can generate a slightly different yaml string
    than the expected string.
    Call this method on expected string to get consistent results.

    Args:
        value: yaml string

    Returns:
        yaml string
    """
    yaml = YAML(typ="rt")
    stream = StringIO()
    yaml.dump(yaml.load(value), stream=stream)
    return stream.getvalue()
