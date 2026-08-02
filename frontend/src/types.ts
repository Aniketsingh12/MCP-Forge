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

/** Collapses a submit → poll → result API into one blocking tool. */
export interface PollingConfig {
  enabled: boolean;
  id_field: string;
  status_path: string;
  status_field: string;
  success_values: string[];
  failure_values: string[];
  interval_seconds: number;
  max_attempts: number;
}

export interface ProposedTool {
  name: string;
  description: string;
  method: string;
  path: string;
  params: ToolParam[];
  confirm_required: boolean;
  enabled: boolean;
  polling: PollingConfig;
}

export interface AuthConfig {
  type: AuthType;
  location: "header" | "query";
  param_name: string;
  value_prefix: string;
}

export type ServerKind = "http" | "python_sdk";

export interface ParseResult {
  api_title: string;
  api_version: string;
  base_url: string;
  server_slug: string;
  auth: AuthConfig;
  tools: ProposedTool[];
  llm_used: boolean;
  kind: ServerKind;
  sdk_module: string;
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

/** A tool as advertised by the running generated MCP server. */
export interface McpTool {
  name: string;
  description: string;
  input_schema: {
    type?: string;
    properties?: Record<string, JsonSchemaProp>;
    required?: string[];
  };
}

export interface JsonSchemaProp {
  type?: string | string[];
  title?: string;
  description?: string;
  default?: unknown;
  anyOf?: { type?: string }[];
}

/** Result of one tools/call round-trip over MCP. */
export interface McpCallResult {
  tool: string;
  args: Record<string, unknown>;
  is_error: boolean;
  structured: unknown;
  text: string;
  latency_ms: number;
}

export interface PublicConfig {
  llm_provider: string;
  llm_model: string;
  llm_enabled: boolean;
  sdk_introspection_enabled: boolean;
  sdk_allowed_modules: string[];
}
