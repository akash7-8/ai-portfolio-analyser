"""Utilities to measure portfolio diversification using HHI.

This module computes:
1. Herfindahl-Hirschman Index (HHI): ``sum(weight^2)``
2. Diversification score: ``(1 - HHI) * 100``

Lower HHI means better diversification, while a higher diversification score
indicates a more diversified portfolio.
"""

from __future__ import annotations

from typing import Iterable, Sequence, Tuple


def calculate_hhi(weights: Sequence[float], tolerance: float = 1e-3) -> float:
	"""Calculate the Herfindahl-Hirschman Index (HHI) for portfolio weights.

	Args:
		weights: Asset weights that should sum approximately to 1.
		tolerance: Allowed absolute error for the sum of weights.

	Returns:
		The HHI value as a float in the range ``[0, 1]`` for valid inputs.

	Raises:
		ValueError: If weights are empty, contain negative values, or if the
			weights do not sum to approximately 1.
	"""
	normalized_weights = _validate_weights(weights, tolerance=tolerance)
	return sum(weight * weight for weight in normalized_weights)


def calculate_diversification(
	weights: Sequence[float], tolerance: float = 1e-3
) -> Tuple[float, float]:
	"""Calculate HHI and diversification score for a portfolio.

	Diversification score formula:
	``(1 - HHI) * 100``

	Args:
		weights: Asset weights that should sum approximately to 1.
		tolerance: Allowed absolute error for the sum of weights.

	Returns:
		A tuple ``(hhi, diversification_score)`` where:
		- ``hhi`` is the Herfindahl-Hirschman Index.
		- ``diversification_score`` is a value on a 0-100 scale.

	Raises:
		ValueError: If input weights fail validation.
	"""
	hhi = calculate_hhi(weights, tolerance=tolerance)
	diversification_score = (1.0 - hhi) * 100.0
	return hhi, diversification_score


def _validate_weights(weights: Iterable[float], tolerance: float = 1e-3) -> list[float]:
	"""Validate portfolio weights and return them as a list.

	Args:
		weights: Input collection of asset weights.
		tolerance: Allowed absolute error for the sum of weights.

	Returns:
		The validated weights as a list of floats.

	Raises:
		ValueError: If input is empty, contains negative values, or the sum of
			weights is not approximately 1.
	"""
	weight_list = [float(weight) for weight in weights]

	if not weight_list:
		raise ValueError("weights must not be empty")

	if any(weight < 0 for weight in weight_list):
		raise ValueError("weights must be non-negative")

	total_weight = sum(weight_list)
	if abs(total_weight - 1.0) > tolerance:
		raise ValueError(
			f"weights must sum to approximately 1.0; got {total_weight:.6f}"
		)

	return weight_list


if __name__ == "__main__":
	# Example usage
	sample_weights = [0.40, 0.25, 0.20, 0.15]
	hhi_value, diversification_score = calculate_diversification(sample_weights)

	print(f"Weights: {sample_weights}")
	print(f"HHI: {hhi_value:.4f}")
	print(f"Diversification Score: {diversification_score:.2f}")

