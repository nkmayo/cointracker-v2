from pathlib import Path
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from cointracker.objects.enumerated_values import OrderingStrategy

DATE_FORMAT = "%Y/%m/%d"


@dataclass
class Paths:
    data: Path
    tests: Path


@dataclass
class Processing:
    ordering_strategy: OrderingStrategy
    wash_rule: bool
    load_existing_pools: bool
    start_date: datetime = None
    end_date: datetime = None
    filing_years: list[int] = field(default_factory=list)
    default_fiat: str = "USD"


@dataclass
class Config:
    paths: Paths
    processing: Processing


def read_config(filepath: str = None) -> Config:
    """Reads the configuration file and returns a configuration object with the settings imported"""
    if filepath is None:
        filepath = (Path(__file__).parents[1] / "settings/config.yaml").resolve()

    # print(f"{filepath=}")
    with open(filepath) as file:
        settings = yaml.safe_load(file)

    base_path = Path(filepath).parents[0]

    paths = settings.get("paths", None)
    paths = {key: ((base_path / value).resolve()) for key, value in paths.items()}
    paths = Paths(**paths)

    processing = settings.get("processing", None)
    processing["ordering_strategy"] = OrderingStrategy.from_str(
        processing["ordering_strategy"]
    )
    if len(processing["start_date"]) > 0:
        processing["start_date"] = datetime.strptime(
            processing["start_date"], DATE_FORMAT
        )
        processing["end_date"] = datetime.strptime(processing["end_date"], DATE_FORMAT)
    else:
        processing["start_date"] = None
        processing["end_date"] = None
    # We have the Paths now, so we can use this to import hte registry?
    processing = Processing(**processing)

    config = Config(paths=paths, processing=processing)

    return config


def fiat_currencies() -> list[str]:
    cfg = read_config()
    fiat_registry_file = cfg.paths.data / "fiat_registry.yaml"
    with open(fiat_registry_file, "r") as file:
        registry = yaml.safe_load(file)

    return [registry[asset]["ticker"] for asset in registry]
