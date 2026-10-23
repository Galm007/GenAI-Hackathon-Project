from __future__ import annotations

from dataclasses import dataclass, field

MAX_ACTIVITIES = 10
MAX_AWARDS = 6
MAX_DESC = 160


@dataclass(frozen=True)
class ProfileFacts:
    applicant_type: str
    intended_major: str | None
    major_category: str
    gpa_uw: float | None
    gpa_w: float | None
    college_gpa: float | None
    sat: int | None
    act: int | None
    advanced_courses: int | None
    rigor_label: str | None
    spike: str | None
    activities: list[tuple[int, str]] = field(default_factory=list)   # (tier, description)
    awards: list[tuple[str, str]] = field(default_factory=list)       # (level, name)
    hooks: list[str] = field(default_factory=list)
    school_type: str | None = None
    residency_state: str | None = None
    income_bracket: str | None = None
    first_gen: bool | None = None


def _fmt(v, spec: str = "") -> str:
    return "—" if v is None else format(v, spec)


def build_profile_text(f: ProfileFacts) -> str:
    first_gen = "yes" if f.first_gen else "no" if f.first_gen is False else "unknown"
    acts = sorted(f.activities, key=lambda a: a[0])[:MAX_ACTIVITIES]          # strongest tiers first
    lines = [
        f"Applicant type: {f.applicant_type.replace('_', '-')}",
        f"Intended major: {f.intended_major or 'undecided'} [{f.major_category}]",
        (f"Academics: UW GPA {_fmt(f.gpa_uw, '.2f')} | W GPA {_fmt(f.gpa_w, '.2f')} | "
         f"{'College GPA ' + _fmt(f.college_gpa, '.2f') + ' | ' if f.college_gpa else ''}"
         f"SAT {_fmt(f.sat)} | ACT {_fmt(f.act)} | advanced courses {_fmt(f.advanced_courses)} | "
         f"rigor {f.rigor_label or 'unknown'}"),
        f"Spike: {f.spike or 'none stated'}",
        "Activities:",
        *[f"- [Tier {t}] {d[:MAX_DESC]}" for t, d in acts],
        "Awards:",
        *[f"- [{lvl}] {name[:MAX_DESC]}" for lvl, name in f.awards[:MAX_AWARDS]],
        (f"Context: {f.school_type or 'unknown'} school; {f.residency_state or 'unknown state'}; "
         f"income {f.income_bracket or 'unknown'}; first-gen {first_gen}"),
        f"Hooks: {', '.join(sorted(f.hooks)) or 'none'}",
    ]
    return "\n".join(lines)
