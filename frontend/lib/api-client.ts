import type {
  AnalysisSummary,
  CashFlowModelResponse,
  CreateCashFlowModelRequest,
  EvaluateDecisionTreeRequest,
  EvaluateDecisionTreeResponse,
  EvaluateScenariosRequest,
  EvaluateScenariosResponse,
  MonteCarloResponse,
  RankOptionsRequest,
  RankOptionsResponse,
  RunMonteCarloRequest,
  SensitivityRequest,
  SensitivityResponse,
} from "./types";

// Requests are routed through the Next.js rewrite in next.config.js
// (/backend/* -> API base URL) so the browser never needs the backend's
// real origin and CORS stays simple in local dev.
const API_BASE = "/backend/api/v1";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

// STUB IDENTITY: mirrors the backend's stub auth dependency
// (shared_kernel/infrastructure/auth.py). Replace with real session-derived
// values once OIDC is wired up — every call site here goes through this one
// function, so that's a one-line change, not a hunt-and-replace.
function devPrincipalHeaders(): HeadersInit {
  return {
    "X-Tenant-Id": "00000000-0000-0000-0000-000000000001",
    "X-User-Id": "00000000-0000-0000-0000-000000000002",
  };
}

async function request<TResponse>(path: string, body: unknown): Promise<TResponse> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...devPrincipalHeaders(),
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, payload.detail ?? "Request failed");
  }

  return res.json() as Promise<TResponse>;
}

async function getRequest<TResponse>(path: string): Promise<TResponse> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "GET",
    headers: devPrincipalHeaders(),
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, payload.detail ?? "Request failed");
  }

  return res.json() as Promise<TResponse>;
}

async function deleteRequest<TResponse>(path: string): Promise<TResponse> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: devPrincipalHeaders(),
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, payload.detail ?? "Request failed");
  }

  return res.json() as Promise<TResponse>;
}

export const financialModelingApi = {
  createCashFlowModel: (req: CreateCashFlowModelRequest) =>
    request<CashFlowModelResponse>("/financial-modeling/cash-flow-models", req),

  listCashFlowModels: () =>
    getRequest<CashFlowModelResponse[]>("/financial-modeling/cash-flow-models"),

  evaluateScenarios: (req: EvaluateScenariosRequest) =>
    request<EvaluateScenariosResponse>("/financial-modeling/scenarios/evaluate", req),

  runSensitivity: (req: SensitivityRequest) =>
    request<SensitivityResponse>("/financial-modeling/sensitivity", req),
};

export const decisionAnalysisApi = {
  rankOptions: (req: RankOptionsRequest) =>
    request<RankOptionsResponse>("/decision-analysis/mcda/rank", req),

  evaluateDecisionTree: (req: EvaluateDecisionTreeRequest) =>
    request<EvaluateDecisionTreeResponse>("/decision-analysis/decision-tree/evaluate", req),

  listAnalyses: () => getRequest<AnalysisSummary[]>("/decision-analysis/analyses"),

  clearHistory: () => deleteRequest<{ deleted_count: number }>("/decision-analysis/analyses"),

  runMonteCarlo: (req: RunMonteCarloRequest) =>
    request<MonteCarloResponse>("/decision-analysis/monte-carlo/run", req),
};
