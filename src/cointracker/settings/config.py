from pathlib import Path
import yaml
from dataclasses import dataclass


@dataclass
class Paths:
    data: Path
    tests: Path


@dataclass
class Config:
    paths: Paths


def read_config(filepath: str = None) -> Config:
    """Reads the configuration file and returns a configuration object with the settings imported"""
    if filepath is None:
        filepath = (Path(__file__).parents[1] / "settings/config.yaml").resolve()

    print(f"{filepath=}")
    with open(filepath) as file:
        settings = yaml.safe_load(file)

    base_path = Path(filepath).parents[0]

    paths = settings.get("paths", None)
    paths = {key: ((base_path / value).resolve()) for key, value in paths.items()}
    paths = Paths(**paths)

    config = Config(paths=paths)

    return config
