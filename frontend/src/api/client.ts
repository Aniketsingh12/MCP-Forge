import type {
  AuthConfig,
  GenerateResult,
  McpCallResult,
  McpTool,
  ParseResult,
  ProjectState,
  ProposedTool,
  PublicConfig,
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

  parseSdk: (id: string, payload: { module: string; use_llm?: boolean }) =>
    req<ParseResult>(`/api/projects/${id}/parse-sdk`, {
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
      kind?: string;
      sdk_module?: string;
    }
  ) =>
    req<GenerateResult>(`/api/projects/${id}/generate`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Playground runs the generated package as a real MCP server over stdio.
  mcpTools: (id: string, payload: { base_url?: string; credential?: string }) =>
    req<{ tools: McpTool[] }>(`/api/playground/${id}/tools`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  mcpCall: (
    id: string,
    payload: {
      base_url?: string;
      credential?: string;
      tool: string;
      args: Record<string, unknown>;
    }
  ) =>
    req<McpCallResult>(`/api/playground/${id}/call`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  downloadUrl: (id: string) => `/api/projects/${id}/download`,
};
