import type {
  AuthConfig,
  GenerateResult,
  ParseResult,
  ProjectState,
  ProposedTool,
  PublicConfig,
  TestToolResult,
} from "../types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  config: () => req<PublicConfig>("/api/config"),

  listProjects: () => req<ProjectState[]>("/api/projects"),
  createProject: (name: string, description = "") =>
    req<ProjectState>("/api/projects", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),
  getProject: (id: string) => req<ProjectState>(`/api/projects/${id}`),
  deleteProject: (id: string) =>
    req<void>(`/api/projects/${id}`, { method: "DELETE" }),

  parse: (
    id: string,
    payload: { spec_text?: string; spec_url?: string; use_llm?: boolean }
  ) =>
    req<ParseResult>(`/api/projects/${id}/parse`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  generate: (
    id: string,
    payload: {
      server_slug: string;
      api_title: string;
      base_url: string;
      auth: AuthConfig;
      tools: ProposedTool[];
    }
  ) =>
    req<GenerateResult>(`/api/projects/${id}/generate`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  testTool: (payload: {
    base_url: string;
    auth: AuthConfig;
    credential: string;
    tool: ProposedTool;
    args: Record<string, unknown>;
  }) =>
    req<TestToolResult>("/api/playground/test", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  downloadUrl: (id: string) => `/api/projects/${id}/download`,
};
