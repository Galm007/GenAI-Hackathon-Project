import importlib
import json

import pytest
from pydantic import BaseModel

from app.schemas.delta import DeltaReport
from app.schemas.dossier import DossierGrade, ParsedDossier, PillarRating
from app.schemas.institution import InstitutionalBrief
from app.schemas.twins import TwinAnalysis

MODULES = ["common", "inputs", "dossier", "institution", "twins", "debate", "delta"]
LLM_OUTPUT_MODELS = [ParsedDossier, DossierGrade, InstitutionalBrief, TwinAnalysis, DeltaReport]


def _all_models() -> list[type[BaseModel]]:
    models = []
    for name in MODULES:
        mod = importlib.import_module(f"app.schemas.{name}")
        models += [v for v in vars(mod).values()
                   if isinstance(v, type) and issubclass(v, BaseModel) and v is not BaseModel]
    return models


def test_every_model_builds_a_json_schema():
    models = _all_models()
    assert len(models) > 30
    for model in models:
        json.dumps(model.model_json_schema())


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


@pytest.mark.parametrize("model", LLM_OUTPUT_MODELS, ids=lambda m: m.__name__)
def test_llm_output_models_have_no_free_form_dicts(model):
    # dict[str, X] becomes an object with additionalProperties, which structured outputs can't enforce.
    for node in _walk(model.model_json_schema()):
        if node.get("type") == "object":
            assert "properties" in node, f"{model.__name__}: open object {node}"
            assert node.get("additionalProperties") in (None, False), f"{model.__name__}: dict field {node}"


def test_pillar_rating_numeric():
    r = PillarRating(rationale="", evidence=[], rating=2, modifier="+")
    assert r.numeric == pytest.approx(1.67)
    assert r.model_copy(update={"modifier": "-"}).numeric == pytest.approx(2.33)
