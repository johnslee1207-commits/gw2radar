from collections import defaultdict

from gw2radar.bors.decision_engine import Decision, DecisionFactor, DecisionRecord


class WeightCalibrator:
    def __init__(self, learning_rate: float = 0.1) -> None:
        self._learning_rate = learning_rate
        self._history: list[DecisionRecord] = []

    def record(self, record: DecisionRecord) -> None:
        self._history.append(record)

    def calibrate(self) -> dict[str, float]:
        if len(self._history) < 3:
            return {}

        factor_outcomes: dict[str, list[bool]] = defaultdict(list)

        for record in self._history:
            actual_positive = record.decision in (Decision.APPROVE, Decision.CERTIFY)
            for factor in record.factors:
                factor_positive = factor.value >= 0.5
                factor_outcomes[factor.name].append(actual_positive == factor_positive)

        adjusted_weights: dict[str, float] = {}
        for fname, outcomes in factor_outcomes.items():
            accuracy = sum(outcomes) / len(outcomes)
            weight_delta = (accuracy - 0.5) * self._learning_rate
            original_weight = self._find_original_weight(fname)
            new_weight = max(0.05, min(1.0, original_weight + weight_delta))
            adjusted_weights[fname] = round(new_weight, 4)

        return adjusted_weights

    def _find_original_weight(self, factor_name: str) -> float:
        for record in self._history:
            for factor in record.factors:
                if factor.name == factor_name:
                    return factor.weight
        return 0.25

    def factor_accuracy(self, factor_name: str) -> float:
        outcomes: list[bool] = []
        for record in self._history:
            actual_positive = record.decision in (Decision.APPROVE, Decision.CERTIFY)
            for factor in record.factors:
                if factor.name == factor_name:
                    factor_positive = factor.value >= 0.5
                    outcomes.append(actual_positive == factor_positive)
        if not outcomes:
            return 0.0
        return sum(outcomes) / len(outcomes)

    def summary(self) -> dict:
        factor_names: set[str] = set()
        for record in self._history:
            for factor in record.factors:
                factor_names.add(factor.name)
        return {
            "total_decisions": len(self._history),
            "factor_count": len(factor_names),
            "factors": sorted(factor_names),
            "calibrated_weights": self.calibrate(),
        }
