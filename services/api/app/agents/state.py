from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from app.schemas.debate import DebateTurn
from app.schemas.delta import Counterfactual, DeltaReport, ProbabilityBreakdown
from app.schemas.dossier import ComputedMetrics, DossierGrade, ParsedDossier
from app.schemas.inputs import RawApplicantInputs
from app.schemas.institution import InstitutionalBrief, SchoolRubric, WebSnippet
from app.schemas.twins import EmpiricalBaseline, TwinAnalysis, TwinCard
from app.scoring.probability import ScoringInputs


class AdComState(TypedDict, total=False):
    # ---- run identity & inputs (set by the API before graph.astream) ----
    run_id: str
    session_id: str
    inputs: RawApplicantInputs           # intake form + base64 PDFs (bytes never persisted)
    school_slug: str                     # one target school per graph run; the UI runs several in sequence

    # ---- Node 1 ----
    dossier: ParsedDossier
    grade: DossierGrade
    metrics: ComputedMetrics
    profile_text: str
    profile_embedding: list[float]

    # ---- Node 2 ----
    school: dict[str, Any]               # universities_cds row
    school_rubric: SchoolRubric
    institutional_brief: InstitutionalBrief | None   # None when web research degraded
    web_snippets: list[WebSnippet]       # W1..Wn, citable in the debate as [[web:Wn]]
    zetaris_queries: list[dict]          # Z1..Zn {id, purpose, sql, rows}, citable as [[sql:Zn]] (§2.10.7)

    # ---- Node 3 ----
    twins: list[TwinCard]
    baseline: EmpiricalBaseline
    twin_analysis: TwinAnalysis | None

    # ---- committee docket (deterministic) ----
    scoring_inputs: ScoringInputs
    probability: ProbabilityBreakdown
    docket: str                          # byte-stable JSON packet shared by all debate turns (prompt-cache friendly)
    docket_index: dict[str, list[str]]   # valid citation refs per kind, for the validator

    # ---- Node 4 ----
    debate: Annotated[list[DebateTurn], operator.add]   # reducer: each turn appends
    debate_turn: int

    # ---- Node 5 ----
    counterfactuals: list[Counterfactual]
    delta_report: DeltaReport

    # ---- diagnostics ----
    warnings: Annotated[list[str], operator.add]
