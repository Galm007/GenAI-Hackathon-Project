from app import world_model
from app.scoring.probability import compute_probability

from ..docket import build_docket, build_scoring_inputs, model_section
from ..events import emit
from ..state import AdComState


async def committee_docket_node(state: AdComState) -> dict:
    x = build_scoring_inputs(state)
    prob = compute_probability(x)
    emit("probability", probability=prob.model_dump(), scoring_inputs=x.model_dump())
    # The shared case file (§1.7.3): Nodes 1-3 wrote their sections; this node adds the model and reads them back.
    run_id = state.get("run_id")
    await world_model.append(run_id, "docket", model_section(prob))
    engine = await world_model.sections(run_id)
    docket, index = build_docket(state, prob, engine)
    down = world_model.enabled() and engine is None
    warnings = ["world model unavailable: docket built from run state"] if down else []
    return {"scoring_inputs": x, "probability": prob, "docket": docket, "docket_index": index, "debate_turn": 0,
            "warnings": warnings}
