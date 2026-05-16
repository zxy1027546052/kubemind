import { z } from 'zod';

export const ChatOpsMessageRequestSchema = z.object({
  session_id: z.string().optional(),
  message: z.string().min(1),
});
export type ChatOpsMessageRequest = z.infer<typeof ChatOpsMessageRequestSchema>;

export const RootCauseSchema = z.object({
  title: z.string(),
  confidence: z.number(),
  evidence_count: z.number(),
});
export type RootCause = z.infer<typeof RootCauseSchema>;

export const RemediationStepSchema = z.object({
  step: z.string(),
  description: z.string(),
  requires_human_approval: z.boolean().optional(),
});
export type RemediationStep = z.infer<typeof RemediationStepSchema>;

export const ToolCallSchema = z.object({
  tool: z.string(),
  status: z.string().optional(),
  namespace: z.string().optional(),
  workload: z.string().optional(),
  query: z.string().optional(),
  audit_id: z.number().nullable().optional(),
  duration_ms: z.number().optional(),
});
export type ToolCall = z.infer<typeof ToolCallSchema>;

export const EvidenceSchema = z.object({
  source: z.string(),
  title: z.string(),
  summary: z.string().optional(),
  score: z.number().optional(),
  source_type: z.string().optional(),
  source_id: z.number().optional(),
});
export type Evidence = z.infer<typeof EvidenceSchema>;

export const TraceEntrySchema = z.object({
  agent: z.string(),
  message: z.string(),
});
export type TraceEntry = z.infer<typeof TraceEntrySchema>;

export const ChatOpsMessageResponseSchema = z.object({
  session_id: z.string(),
  intent: z.string(),
  entities: z.record(z.string(), z.string()),
  reply: z.string().optional(),
  trace: z.array(TraceEntrySchema),
  evidence: z.array(EvidenceSchema),
  tool_calls: z.array(ToolCallSchema),
  root_causes: z.array(RootCauseSchema),
  remediation_plan: z.array(RemediationStepSchema),
  requires_human_approval: z.boolean(),
  llm_reply: z.string().optional(),
});
export type ChatOpsMessageResponse = z.infer<typeof ChatOpsMessageResponseSchema>;

export const AgentEventSchema = z.object({
  type: z.enum(['agent.started', 'agent.completed', 'agent.failed']),
  agent: z.string(),
  execution_id: z.string().optional(),
  duration_ms: z.number().optional(),
  status: z.string().optional(),
  error: z.string().optional(),
  timestamp: z.string(),
});
export type AgentEvent = z.infer<typeof AgentEventSchema>;

export const ToolEventSchema = z.object({
  type: z.enum(['tool.started', 'tool.completed', 'tool.failed', 'tool.stdout']),
  tool: z.string(),
  execution_id: z.string().optional(),
  agent_execution_id: z.string().optional(),
  args: z.record(z.string(), z.unknown()).optional(),
  duration_ms: z.number().optional(),
  risk_level: z.string().optional(),
  chunk: z.string().optional(),
  error: z.string().optional(),
  timestamp: z.string(),
});
export type ToolEvent = z.infer<typeof ToolEventSchema>;

export const EvidenceEventSchema = z.object({
  type: z.literal('evidence.added'),
  source: z.string(),
  title: z.string(),
  summary: z.string(),
  timestamp: z.string(),
});
export type EvidenceEvent = z.infer<typeof EvidenceEventSchema>;

export const DiagnosisEventSchema = z.object({
  type: z.literal('diagnosis.updated'),
  root_causes: z.array(z.object({
    title: z.string(),
    confidence: z.number(),
    evidence_count: z.number(),
  })).optional(),
  remediation_plan: z.array(z.object({
    step: z.string(),
    description: z.string(),
    requires_human_approval: z.boolean(),
  })).optional(),
  timestamp: z.string(),
});
export type DiagnosisEvent = z.infer<typeof DiagnosisEventSchema>;

export const RuntimeEventSchema = z.union([
  AgentEventSchema,
  ToolEventSchema,
  EvidenceEventSchema,
  DiagnosisEventSchema,
]);
export type RuntimeEvent = z.infer<typeof RuntimeEventSchema>;
