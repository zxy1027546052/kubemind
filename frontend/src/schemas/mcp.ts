import { z } from 'zod';

export const ToolExecuteRequestSchema = z.object({
  tool_name: z.string().min(1),
  params: z.record(z.string(), z.unknown()).optional(),
  session_id: z.string().optional(),
  trace_id: z.string().optional(),
  namespace: z.string().optional(),
});
export type ToolExecuteRequest = z.infer<typeof ToolExecuteRequestSchema>;

export const ToolExecuteResponseSchema = z.object({
  success: z.boolean(),
  result: z.unknown().optional(),
  error: z.string().optional(),
  duration_ms: z.number(),
  audit_id: z.number().nullable().optional(),
});
export type ToolExecuteResponse = z.infer<typeof ToolExecuteResponseSchema>;
