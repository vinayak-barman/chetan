from typing import Dict, List, Optional, Tuple, Any, Literal, Union
from chetan.agent import AgentLoop
from chetan.entity import Persona, SystemEntities
from chetan.align import Rule


from pydantic import BaseModel
import yaml
import os

from chetan.lm import LanguageModel
from chetan.system import System


class LLMConfig(BaseModel):
    provider: Literal["openai", "anthropic", "groq", "cohere", "kendra"]
    credentials: dict


class RuleConfig(BaseModel):
    description: str
    nature: Literal["positive", "negative"]


class EntityConfig(BaseModel):
    description: str
    rules: Optional[List[str]]
    type: Literal["human", "agent"]
    config: Dict[str, Union[str, int, bool, dict]]


class SystemConfig(BaseModel):
    description: str
    entities: List[str]
    topology: Literal["sequential", "mesh", "hierarchy", "network"]


class Config(BaseModel):
    lm: Dict[str, LLMConfig]
    rules: Dict[str, RuleConfig]
    entities: Dict[str, EntityConfig]
    systems: Dict[str, SystemConfig]


def process_lm(cfg: LLMConfig):
    provider = cfg.provider

    if provider == "openai":
        pass

    pass


def process_rules(cfg: RuleConfig):
    pass


def process_entities(cfg: EntityConfig):
    pass


def process_systems(cfg: SystemConfig):
    pass


def get_entity_type(entity: dict):
    return entity.get("type", "agent")


def load_yaml_config(
    path: str, agent_loops: Dict[str, AgentLoop]
) -> Tuple[
    Dict[str, LanguageModel], Dict[str, Rule], SystemEntities, Dict[str, System]
]:
    """Loads a yaml config file from `path` and returns a dictionary of rules, system personas, and LM configurations.

    Args:
        path (str): The path where the config is stored
        agent_loops (Dict[str, AgentLoop]): A dictionary of agent loops

    Returns:
        Tuple[Dict[str, Rule], SystemPersonas, Dict[str, Any]]: A tuple with rules, system personas, and LM configurations
    """
    try:
        with open(path, "r") as f:
            cfg = yaml.safe_load(f)  # Use safe_load for security
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found at {path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {e}")

    try:
        config = Config(**cfg)
    except ValueError as e:
        raise ValueError(f"Invalid config structure: {e}")

    language_models: Dict[str, LanguageModel] = {}
    rules: Dict[str, Rule] = {}
    entities: SystemEntities = SystemEntities()
    systems: Dict[str, System] = {}

    # 1. Load language models
    for name, cfg in config.lm.items():
        language_models[name] = process_lm(name, cfg)

    # 2. Load rules
    for name, cfg in config.rules.items():
        rules[name] = process_rules(cfg)

    # 3. Load entities
    for name, cfg in config.entities.items():
        entity_type = get_entity_type(cfg)
        if entity_type == "agent":
            entities.agents[name] = process_entities(cfg)
        elif entity_type == "human":
            entities.humans[name] = process_entities(cfg)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

    # 4. Load systems
    for name, cfg in config.systems.items():
        systems[name] = process_systems(cfg)
