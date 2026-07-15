// Types mirror sdie/financial_modeling/interface/schemas.py and
// sdie/decision_analysis/interface/schemas.py exactly. If the backend
// schema changes, update here — this is the single seam between the two
// codebases, deliberately kept explicit rather than code-generated so a
// reviewer can diff intent, not just shape.

export interface CashFlowInput {
  period: number;
  amount: string; // Decimal serialized as string to avoid float precision loss in transit
}

export interface CreateCashFlowModelRequest {
  project_name: string;
  currency: string;
  discount_rate_percent: string;
  cash_flows: CashFlowInput[];
}

export interface CashFlowModelResponse {
  model_id: string;
  project_name: string;
  currency: string;
  discount_rate_percent: string;
  npv: string;
  irr_percent: string | null;
  payback_period: string | null;
}

export interface ScenarioInput {
  name: string;
  cash_flows: CashFlowInput[];
  probability_percent?: string | null;
}

export interface EvaluateScenariosRequest {
  project_name: string;
  currency: string;
  discount_rate_percent: string;
  scenarios: ScenarioInput[];
}

export interface ScenarioOutcome {
  name: string;
  npv: string;
  irr_percent: string | null;
  probability_percent: string | null;
}

export interface EvaluateScenariosResponse {
  outcomes: ScenarioOutcome[];
  probability_weighted_npv: string | null;
}

export interface SensitivityRequest {
  currency: string;
  discount_rate_percent: string;
  base_cash_flows: CashFlowInput[];
  variable_name: string;
  variable_period: number;
  low_amount: string;
  base_amount: string;
  high_amount: string;
}

export interface SensitivityResponse {
  variable: string;
  npv_low: string;
  npv_base: string;
  npv_high: string;
  swing: string;
}

// --- decision analysis ---

export interface CriterionInput {
  name: string;
  weight: number;
  higher_is_better: boolean;
}

export interface MCDAOptionInput {
  name: string;
  scores: Record<string, number>;
}

export interface RankOptionsRequest {
  title: string;
  criteria: CriterionInput[];
  options: MCDAOptionInput[];
}

export interface MCDARanking {
  option: string;
  weighted_score: number;
  normalized_scores: Record<string, number>;
}

export interface RankOptionsResponse {
  analysis_id: string;
  rankings: MCDARanking[];
  recommended_option: string;
}

export interface OutcomeInput {
  name: string;
  probability: number;
  payoff: number;
}

export interface DecisionOptionInput {
  name: string;
  outcomes: OutcomeInput[];
}

export interface EvaluateDecisionTreeRequest {
  title: string;
  options: DecisionOptionInput[];
}

export interface EvaluateDecisionTreeResponse {
  analysis_id: string;
  ranked_options: [string, number][];
  recommended_option: string;
  expected_value_with_perfect_info: number;
  expected_value_of_perfect_information: number;
}
