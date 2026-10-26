from __future__ import annotations

import json

from app import llm, zetaris_repo

from .events import tool_call

MAX_QUERIES = 3

ZETARIS_SQL_TOOL = {
    "name": "zetaris_sql",
    "description": (
        "Run ONE read-only Spark SQL SELECT against the AdCom semantic layer in Zetaris Lightning and get up to "
        "50 rows back (values are strings). Views:\n"
        "- ADCOM.v_school_profile(slug, name, state, control, peer_group, admit_rate, admit_rate_source, "
        "ed_admit_rate, rd_admit_rate, sat_composite_25, sat_composite_75, test_policy, c7_source, cds_year, "
        "undergrad_enrollment)\n"
        "- ADCOM.v_school_c7_long(slug, name, c7_source, factor, level)\n"
        "- ADCOM.v_major_stats(slug, major_category, n, n_accepted, n_waitlisted, n_rejected, reddit_admit_rate, "
        "school_reddit_admit_rate, smoothed_multiplier)\n"
        "- ADCOM.v_reddit_calibration(slug, official_admit_rate, reddit_n, reddit_admit_rate, odds_inflation)\n"
        "- ADCOM.v_admitted_medians(slug, n, gpa_uw, sat, advanced, ec_rating, spike_points)\n"
        "- ADCOM.v_peer_benchmarks(slug, name, peer_group, admit_rate, sat_composite_25, sat_composite_75, "
        "peer_n, peer_median_admit_rate, peer_median_sat_75)\n"
        "Use single quotes for string literals. Always filter or aggregate; never select whole views."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "purpose": {"type": "string", "description": "One sentence: what this query checks and why."},
            "sql": {"type": "string"},
        },
        "required": ["purpose", "sql"],
        "additionalProperties": False,
    },
}

INSTITUTIONAL_SQL_SYSTEM = """\
You are the institutional research analyst for a simulated admissions committee, with read-only SQL access \
to the AdCom semantic layer in Zetaris Lightning through the zetaris_sql tool. You may run at most three \
queries. Choose the ones that most change how the committee should read this applicant at this school:
- how the school compares with its peer group (selectivity, test band),
- how applicants in the applicant's major category fare there (sample size matters; say so when n < 15),
- where the C7 weights come from (CDS vs. the coarser IPEDS fallback) and what they emphasize.
Query only the listed views. When you have what you need, stop calling the tool and reply with a short \
plain-text summary of what you found."""


async def run_zetaris_research(*, slug: str, major_category: str, applicant_summary: str) -> list[dict]:
    """Bounded manual tool loop; returns [{id, purpose, sql, rows, error}] for the brief and the docket."""
    findings: list[dict] = []
    messages: list[dict] = [{"role": "user", "content": (
        f"Target school slug: '{slug}'. Applicant major category: '{major_category}'.\n"
        f"Applicant summary: {applicant_summary}\nInvestigate.")}]

    for _ in range(MAX_QUERIES + 1):
        turn = await llm.chat_with_tools(system=INSTITUTIONAL_SQL_SYSTEM, messages=messages,
                                         tools=[ZETARIS_SQL_TOOL], name="zetaris research")
        messages.append({"role": "assistant", "turn": turn})
        if not turn.calls:
            break

        results = []
        for call in turn.calls:
            if len(findings) >= MAX_QUERIES:
                results.append({"id": call.id, "is_error": True,
                                "content": "Query budget used up. Summarize what you found."})
                continue
            fid = f"Z{len(findings) + 1}"
            sql, purpose = str(call.input.get("sql", "")), str(call.input.get("purpose", ""))
            tool_call("institutional", "zetaris.sql", "started", id=fid, purpose=purpose, sql=sql)
            try:
                safe_sql, rows = await zetaris_repo.agent_query(sql)
                findings.append({"id": fid, "purpose": purpose, "sql": safe_sql, "rows": rows[:20], "error": None})
                tool_call("institutional", "zetaris.sql", "done", id=fid, result_count=len(rows))
                results.append({"id": call.id, "content": json.dumps(rows[:50])[:12000]})
            except (zetaris_repo.SqlNotAllowed, *zetaris_repo.UNAVAILABLE) as exc:   # down stack = failed query (D-039)
                tool_call("institutional", "zetaris.sql", "failed", id=fid, error=str(exc)[:200])
                results.append({"id": call.id, "is_error": True, "content": f"Query rejected: {exc}"})
        messages.append({"role": "tool_results", "results": results})
    return findings
