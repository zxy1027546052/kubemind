import { z } from 'zod';

export const AlertCreateSchema = z.object({
  title: z.string().min(1),
  description: z.string().optional(),
  severity: z.string().optional(),
  source: z.string().optional(),
  status: z.string().optional(),
  assigned_to: z.string().optional(),
  category: z.string().optional(),
});
export type AlertCreate = z.infer<typeof AlertCreateSchema>;

export const AlertUpdateSchema = AlertCreateSchema.partial();
export type AlertUpdate = z.infer<typeof AlertUpdateSchema>;

export const AlertResponseSchema = z.object({
  id: z.number(),
  title: z.string(),
  description: z.string(),
  severity: z.string(),
  source: z.string(),
  status: z.string(),
  assigned_to: z.string(),
  category: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type AlertResponse = z.infer<typeof AlertResponseSchema>;
