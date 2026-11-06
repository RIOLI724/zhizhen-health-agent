export type Role = "user" | "assistant";

export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
}

export interface EmergencyData {
  level: string;
  title: string;
  desc: string;
  department?: string;
  timeframe?: string;
  cta: string;
}

export interface RiskData {
  level: string;
  department: string;
  timeframe: string;
  note: string;
  evidence: string[];
}

export type ProfileRelation = "self" | "family";
export type ProfileSex = "male" | "female" | "other" | "";

export interface SessionProfile {
  relation: ProfileRelation;
  age: string;
  sex: ProfileSex;
  pregnant: boolean;
}

export interface ReportImagePayload {
  data: string;
  mime: string;
  name?: string;
}

export interface HealthProfile {
  id: string;
  relation: "self" | "family";
  label: string;
  age: string;
  sex: ProfileSex;
  pregnant: boolean;
}

export interface SavedReport {
  id: string;
  title: string;
  source: "upload" | "sample";
  date: number;
  rows: ReportRow[];
  note: string;
  interpretation: string;
  citations: string[];
}

export type ReportFlag = "high" | "low" | "normal";

export interface ReportRow {
  name: string;
  value: string;
  unit: string;
  range: string;
  flag: ReportFlag;
}

export interface ReportData {
  title: string;
  rows: ReportRow[];
  note: string;
}

export interface ChatMessageImage {
  data: string;
  mime: string;
}

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  toolCalls: ToolCall[];
  citations: string[];
  chips: string[];
  emergency?: EmergencyData;
  report?: ReportData;
  risk?: RiskData;
  image?: ChatMessageImage;
  fromImage?: boolean;
  streaming: boolean;
  error?: string;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  updatedAt: number;
}

export interface ChatHistoryItem {
  role: Role;
  content: string;
}

export type ChatEvent =
  | { type: "status"; stage: string }
  | { type: "tool_call"; name: string; arguments: Record<string, unknown> }
  | { type: "delta"; content: string }
  | { type: "replace"; content: string }
  | { type: "chips"; items: string[] }
  | { type: "citations"; items: string[] }
  | { type: "emergency"; data: EmergencyData }
  | { type: "report"; data: ReportData }
  | { type: "risk"; data: RiskData }
  | { type: "done" }
  | { type: "error"; detail: string };
