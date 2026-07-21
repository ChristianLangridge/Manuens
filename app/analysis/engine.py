from app.analysis.ambiguities import find_ambiguities
from app.analysis.deviations import find_deviations
from app.analysis.gaps import find_gaps
from app.models import AnalysisResult, ExtractedRun, Protocol

_RECOVERABILITY_ORDER = {"perishable_now": 0, "perishable_today": 1, "stable": 2}


def analyse_run(protocol: Protocol, run: ExtractedRun) -> AnalysisResult:
    findings = [
        *find_gaps(protocol, run),
        *find_deviations(protocol, run),
        *find_ambiguities(protocol, run),
    ]
    findings.sort(key=lambda f: _RECOVERABILITY_ORDER[f.recoverability])

    flagged_step_ids = {f.step_id for f in findings if f.step_id is not None}
    clean_step_ids = [
        extracted_step.step_id
        for extracted_step in run.steps
        if extracted_step.step_id not in flagged_step_ids
    ]

    return AnalysisResult(findings=findings, clean_step_ids=clean_step_ids)
