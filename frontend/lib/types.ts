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
  industry?: string | null;
}

export interface CashFlowModelResponse {
  model_id: string;
  project_name: string;
  currency: string;
  discount_rate_percent: string;
  npv: string;
  irr_percent: string | null;
  payback_period: string | null;
  flags: string[];
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

export interface WeightRobustness {
  criterion: string;
  current_weight: number;
  flips_at_weight: number | null;
  direction: string;
}

export interface RankOptionsResponse {
  analysis_id: string;
  rankings: MCDARanking[];
  recommended_option: string;
  weight_robustness: WeightRobustness[];
  flags: string[];
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

export interface ProbabilityBreakeven {
  outcome_name: string;
  option_a: string;
  option_b: string;
  breakeven_probability: number | null;
}

export interface EvaluateDecisionTreeResponse {
  analysis_id: string;
  ranked_options: [string, number][];
  recommended_option: string;
  expected_value_with_perfect_info: number;
  expected_value_of_perfect_information: number;
  flags: string[];
  probability_breakeven: ProbabilityBreakeven | null;
}

export interface AnalysisSummary {
  analysis_id: string;
  title: string;
  method: string;
  recommended_option: string;
  result_data: Record<string, unknown>;
  created_at: string;
}

// --- Monte Carlo ---

export type DistributionKind = "normal" | "triangular" | "uniform" | "lognormal";

export interface DistributionInput {
  name: string;
  kind: DistributionKind;
  params: number[];
}

export interface RunMonteCarloRequest {
  title: string;
  variables: DistributionInput[];
  fixed_costs: number;
  iterations: number;
  seed: number;
}

export interface HistogramBin {
  bin_start: number;
  bin_end: number;
  count: number;
}

export interface MonteCarloResponse {
  analysis_id: string;
  iterations: number;
  seed: number;
  mean: number;
  std_dev: number;
  percentile_5: number;
  percentile_50: number;
  percentile_95: number;
  probability_negative: number;
  histogram: HistogramBin[];
}

// --- evidence research ---

export interface IngestDocumentRequest {
  title: string;
  source_label: string;
  content: string;
}

export interface DocumentResponse {
  document_id: string;
  title: string;
  source_label: string;
  created_at: string;
}

export interface SearchEvidenceRequest {
  query: string;
  limit?: number;
}

export interface CitationResponse {
  document_id: string;
  document_title: string;
  source_label: string;
  excerpt: string;
  relevance_score: number;
}

// --- recommendation synthesis ---

export type QuantContext = "financial_modeling" | "decision_analysis";

export interface EvidenceCitationSchema {
  document_id: string;
  document_title: string;
  source_label: string;
  excerpt: string;
  relevance_score: number;
}

export interface CreateRationaleRequest {
  title: string;
  quant_context: QuantContext;
  quant_analysis_id: string;
  recommended_option: string;
  confidence_note: string;
  evidence_citations: EvidenceCitationSchema[];
}

export interface OverrideSchema {
  overridden_by: string;
  reason: string;
  new_recommended_option: string;
  overridden_at: string;
}

export interface RationaleResponse {
  rationale_id: string;
  title: string;
  quant_context: string;
  quant_analysis_id: string;
  recommended_option: string;
  current_recommendation: string;
  confidence_note: string;
  evidence_citations: EvidenceCitationSchema[];
  overrides: OverrideSchema[];
  created_at: string;
}

export interface OverrideRationaleRequest {
  overridden_by: string;
  reason: string;
  new_recommended_option: string;
}

export interface NarrativeResponse {
  rationale_id: string;
  narrative: string;
}

// --- problem framing ---

export type Framework = "five_forces" | "swot";

export interface FrameworkSectionSchema {
  key: string;
  label: string;
  guiding_question: string;
}

export interface CreateFrameworkAnalysisRequest {
  title: string;
  framework: Framework;
  entries: Record<string, string[]>;
}

export interface FrameworkAnalysisResponse {
  analysis_id: string;
  title: string;
  framework: string;
  entries: Record<string, string[]>;
  completion_ratio: number;
  created_at: string;
}

// --- workspace ---

export type EngagementStatus =
  | "framing"
  | "evidence_gathering"
  | "quant_analysis"
  | "synthesis"
  | "complete";

export interface CreateEngagementRequest {
  title: string;
}

export interface EngagementResponse {
  engagement_id: string;
  title: string;
  status: EngagementStatus;
  problem_framing_analysis_id: string | null;
  evidence_document_ids: string[];
  financial_model_id: string | null;
  decision_analysis_id: string | null;
  rationale_id: string | null;
  created_at: string;
}

export interface LinkProblemFramingRequest {
  analysis_id: string;
}

export interface AddEvidenceRequest {
  document_id: string;
}

export interface LinkFinancialModelRequest {
  model_id: string;
}

export interface LinkDecisionAnalysisRequest {
  analysis_id: string;
}

export interface LinkRationaleRequest {
  rationale_id: string;
}
