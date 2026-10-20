from app.schemas.finding import Finding


def merge_duplicate_candidates(results: list[dict]) -> list[Finding]:
    merged: list[Finding] = []
    for result in results:
        agent = result["task"]
        for finding in result["findings"]:
            match = next((item for item in merged if item.category == finding.category and item.file_path == finding.file_path and item.start_line is not None and finding.start_line is not None and item.end_line is not None and finding.end_line is not None and item.start_line <= finding.end_line and finding.start_line <= item.end_line), None)
            if match is None:
                merged.append(finding.model_copy(update={"supporting_agents": sorted(set(finding.supporting_agents + [agent]))}))
                continue
            merged[merged.index(match)] = match.model_copy(update={"supporting_agents": sorted(set(match.supporting_agents + finding.supporting_agents + [agent])), "supporting_tools": sorted(set(match.supporting_tools + finding.supporting_tools)), "supporting_rule_ids": sorted(set(match.supporting_rule_ids + finding.supporting_rule_ids))})
    return merged
