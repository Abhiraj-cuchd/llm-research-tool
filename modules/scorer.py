from utils.validators import Codebook, CodingResult, ParticipantScore


def normalise_weights(dimensions) -> dict[str, float]:
    total = sum(d.weight for d in dimensions)
    if total == 0:
        count = len(dimensions)
        return {d.id: 1.0 / count for d in dimensions} if count > 0 else {}
    return {d.id: d.weight / total for d in dimensions}


def compute_scores(result: CodingResult, codebook: Codebook) -> ParticipantScore:
    weights = normalise_weights(codebook.dimensions)
    max_scale = codebook.scale

    dimension_scores = {}
    weighted_sum = 0.0

    for dim in codebook.dimensions:
        ds = result.dimensions.get(dim.id)
        if ds:
            normalised = (ds.score / max_scale) * 100
            dimension_scores[dim.id] = normalised
            weighted_sum += normalised * weights.get(dim.id, 0)
        else:
            dimension_scores[dim.id] = 0.0

    return ParticipantScore(
        participant=result.participant,
        dimension_scores=dimension_scores,
        overall=round(weighted_sum, 2),
    )


def rank_participants(scores: dict[str, ParticipantScore]) -> list[tuple[str, float]]:
    return sorted(
        [(pid, ps.overall) for pid, ps in scores.items()],
        key=lambda x: x[1],
        reverse=True,
    )


def dimension_averages(scores: dict[str, ParticipantScore]) -> dict[str, float]:
    if not scores:
        return {}
    dim_ids = next(iter(scores.values())).dimension_scores.keys()
    averages = {}
    for dim_id in dim_ids:
        vals = [ps.dimension_scores.get(dim_id, 0) for ps in scores.values()]
        averages[dim_id] = round(sum(vals) / len(vals), 2) if vals else 0.0
    return averages
