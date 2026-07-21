import type {
  AddEvidenceRequest,
  AnalysisSummary,
  CashFlowModelResponse,
  CitationResponse,
  CreateCashFlowModelRequest,
  CreateEngagementRequest,
  CreateFrameworkAnalysisRequest,
  CreateRationaleRequest,
  DocumentResponse,
  EngagementResponse,
  EvaluateDecisionTreeRequest,
  EvaluateDecisionTreeResponse,
  EvaluateScenariosRequest,
  EvaluateScenariosResponse,
  FrameworkAnalysisResponse,
  FrameworkSectionSchema,
  IngestDocumentRequest,
  LinkDecisionAnalysisRequest,
  LinkFinancialModelRequest,
  LinkProblemFramingRequest,
  LinkRationaleRequest,
  MonteCarloResponse,
  NarrativeResponse,
  OverrideRationaleRequest,
  RankOptionsRequest,
  RankOptionsResponse,
  RationaleResponse,
  RunMonteCarloRequest,
  SearchEvidenceRequest,
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

async function getBlobRequest(path: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "GET",
    headers: devPrincipalHeaders(),
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, payload.detail ?? "Request failed");
  }

  return res.blob();
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

export const evidenceResearchApi = {
  ingestDocument: (req: IngestDocumentRequest) =>
    request<DocumentResponse>("/evidence-research/documents", req),

  listDocuments: () => getRequest<DocumentResponse[]>("/evidence-research/documents"),

  searchEvidence: (req: SearchEvidenceRequest) =>
    request<CitationResponse[]>("/evidence-research/search", req),

  clearHistory: () => deleteRequest<{ deleted_count: number }>("/evidence-research/documents"),
};

export const recommendationSynthesisApi = {
  createRationale: (req: CreateRationaleRequest) =>
    request<RationaleResponse>("/recommendation-synthesis/rationales", req),

  listRationales: () => getRequest<RationaleResponse[]>("/recommendation-synthesis/rationales"),

  getRationale: (id: string) =>
    getRequest<RationaleResponse>(`/recommendation-synthesis/rationales/${id}`),

  overrideRationale: (id: string, req: OverrideRationaleRequest) =>
    request<RationaleResponse>(`/recommendation-synthesis/rationales/${id}/override`, req),

  generateNarrative: (id: string) =>
    request<NarrativeResponse>(`/recommendation-synthesis/rationales/${id}/narrative`, {}),

  downloadOnePager: (id: string) =>
    getBlobRequest(`/recommendation-synthesis/rationales/${id}/one-pager`),

  clearHistory: () =>
    deleteRequest<{ deleted_count: number }>("/recommendation-synthesis/rationales"),
};

export const problemFramingApi = {
  getTemplate: (framework: string) =>
    getRequest<FrameworkSectionSchema[]>(`/problem-framing/templates/${framework}`),

  createAnalysis: (req: CreateFrameworkAnalysisRequest) =>
    request<FrameworkAnalysisResponse>("/problem-framing/analyses", req),

  listAnalyses: () => getRequest<FrameworkAnalysisResponse[]>("/problem-framing/analyses"),

  getAnalysis: (id: string) =>
    getRequest<FrameworkAnalysisResponse>(`/problem-framing/analyses/${id}`),

  clearHistory: () => deleteRequest<{ deleted_count: number }>("/problem-framing/analyses"),
};

export const workspaceApi = {
  createEngagement: (req: CreateEngagementRequest) =>
    request<EngagementResponse>("/workspace/engagements", req),

  listEngagements: () => getRequest<EngagementResponse[]>("/workspace/engagements"),

  getEngagement: (id: string) => getRequest<EngagementResponse>(`/workspace/engagements/${id}`),

  linkProblemFraming: (id: string, req: LinkProblemFramingRequest) =>
    request<EngagementResponse>(`/workspace/engagements/${id}/link-problem-framing`, req),

  addEvidence: (id: string, req: AddEvidenceRequest) =>
    request<EngagementResponse>(`/workspace/engagements/${id}/link-evidence`, req),

  linkFinancialModel: (id: string, req: LinkFinancialModelRequest) =>
    request<EngagementResponse>(`/workspace/engagements/${id}/link-financial-model`, req),

  linkDecisionAnalysis: (id: string, req: LinkDecisionAnalysisRequest) =>
    request<EngagementResponse>(`/workspace/engagements/${id}/link-decision-analysis`, req),

  linkRationale: (id: string, req: LinkRationaleRequest) =>
    request<EngagementResponse>(`/workspace/engagements/${id}/link-rationale`, req),

  clearHistory: () => deleteRequest<{ deleted_count: number }>("/workspace/engagements"),
};

export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
