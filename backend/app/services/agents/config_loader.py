from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

_POLICIES_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "policies"


class ApprovalTierConfig(BaseModel):
    tier: int
    role: str
    title: str
    max_amount: Optional[float]
    currency: str
    scope: str


class ApprovalPoliciesConfig(BaseModel):
    version: str
    institution: str
    policy_name: str
    tiers: List[ApprovalTierConfig]
    escalation_rules: Dict[str, Any]


class MatchingTolerancesConfig(BaseModel):
    version: str
    policy_name: str
    unit_price_tolerance_percentage: float
    quantity_tolerance_units: float
    line_total_tolerance_inr: float
    allow_partial_deliveries: bool
    require_formal_grn: bool
    rules: Dict[str, str]


class FraudThresholdsConfig(BaseModel):
    version: str
    policy_name: str
    score_bands: Dict[str, Dict[str, Any]]
    risk_impact_weights: Dict[str, int]


class VendorRulesConfig(BaseModel):
    version: str
    policy_name: str
    gstin_regex: str
    name_similarity_threshold: float
    requirements: Dict[str, bool]


class TaxRulesConfig(BaseModel):
    version: str
    policy_name: str
    university_home_state_code: str
    university_home_state_name: str
    statutory_gst_rates: List[float]
    max_allowable_roundoff_inr: float
    tax_regime: Dict[str, Any]


class BudgetRulesConfig(BaseModel):
    version: str
    policy_name: str
    current_fiscal_year: str
    thresholds: Dict[str, Any]
    rules: Dict[str, str]


def _read_json_file(filename: str) -> Dict[str, Any]:
    file_path = _POLICIES_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Policy configuration file '{filename}' not found at {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def get_approval_policies() -> ApprovalPoliciesConfig:
    data = _read_json_file("approval_policies.json")
    return ApprovalPoliciesConfig.model_validate(data)


@lru_cache(maxsize=1)
def get_matching_tolerances() -> MatchingTolerancesConfig:
    data = _read_json_file("matching_tolerances.json")
    return MatchingTolerancesConfig.model_validate(data)


@lru_cache(maxsize=1)
def get_fraud_thresholds() -> FraudThresholdsConfig:
    data = _read_json_file("fraud_thresholds.json")
    return FraudThresholdsConfig.model_validate(data)


@lru_cache(maxsize=1)
def get_vendor_verification_rules() -> VendorRulesConfig:
    data = _read_json_file("vendor_verification_rules.json")
    return VendorRulesConfig.model_validate(data)


@lru_cache(maxsize=1)
def get_tax_rules() -> TaxRulesConfig:
    data = _read_json_file("tax_rules.json")
    return TaxRulesConfig.model_validate(data)


@lru_cache(maxsize=1)
def get_department_budget_rules() -> BudgetRulesConfig:
    data = _read_json_file("department_budget_rules.json")
    return BudgetRulesConfig.model_validate(data)

