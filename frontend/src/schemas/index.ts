import { z } from 'zod';

export class ApiValidationError extends Error {
  constructor(
    public readonly path: string,
    public readonly issues: z.ZodIssue[],
  ) {
    super(`API validation failed at ${path}: ${issues.map(i => i.message).join(', ')}`);
    this.name = 'ApiValidationError';
  }
}

export function parseSchema<T>(schema: z.ZodType<T>, data: unknown, path: string): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    throw new ApiValidationError(path, result.error.issues);
  }
  return result.data;
}

export * from './chatops';
export * from './alerts';
export * from './mcp';
