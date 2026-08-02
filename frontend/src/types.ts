// Mirrors backend Pydantic models. Tools are treated largely opaquely and
// round-tripped back to the server unchanged, apart from user edits.

export type AuthType = "none" | "api_key" | "bearer" | "basic";
export type ProjectStatus = "draft" | "proposed" | "generated" | "tested";

export interface ToolParam {
  name: string;
  type: string;
  description: string;
  required: boolean;
  location: "query" | "path" | "header" | "body";
  json_schema?: Record<string, unknown> | null;
}

export interface ProposedTool {
  name: string;
  description: string;
  method: string;
  path: string;
  params: ToolParam[];
  confirm_required: boolean;
  enabled: boolean;
}

export interface AuthConfig {
  type: AuthType;
  location: "header" | "query";
  param_name: string;
  value_prefix: string;
}

export interface ParseResult {
  api_title: string;
  api_version: string;
  base_url: string;
  server_slug: string;
  auth: AuthConfig;
  tools: ProposedTool[];
  llm_used: boolean;
}

export interface GeneratedFile {
  path: string;
  content: string;
  language: string;
}

export interface GenerateResult {
  server_slug: string;
  files: GeneratedFile[];
  valid: boolean;
  validation_messages: string[];
}

export interface ProjectState {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
  parse_result: ParseResult | null;
  generate_result: GenerateResult | null;
}

export interface TestToolResult {
  request_method: string;
  request_url: string;
  request_headers: Record<string, string>;
  request_body: unknown;
  status_code: number | null;
  response_headers: Record<string, string>;
  response_body: unknown;
  normalized: Record<string, unknown>;
  latency_ms: number;
  error: string | null;
}

export interface PublicConfig {
  llm_provider: string;
  llm_model: string;
  llm_enabled: boolean;
}
