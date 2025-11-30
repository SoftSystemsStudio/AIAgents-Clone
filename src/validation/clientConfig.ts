import { z } from 'zod';

export const CompanyProfileSchema = z.object({
  name: z.string().optional(),
  website: z.string().url().optional(),
  industry: z.string().optional(),
  size: z.string().optional(),
  business_model: z.string().optional(),
  objectives: z.array(z.string()).optional(),
  urgency: z.string().optional(),
});

export const StackSchema = z.object({
  website_platform: z.string().optional(),
  crm: z.string().optional(),
  helpdesk: z.string().optional(),
  email: z.string().optional(),
  project_tools: z.array(z.string()).optional(),
  data_sources: z.array(z.string()).optional(),
  comms_tools: z.array(z.string()).optional(),
  telephony: z.string().optional(),
  calendar: z.string().optional(),
  integration_effort_level: z.enum(['low', 'medium', 'high']).optional(),
});

export const SupportSystemSchema = z.object({
  channels: z.array(z.string()),
  expected_daily_volume: z.number().int().nonnegative(),
  ai_allowed_topics: z.array(z.string()),
  escalation_policies: z.array(z.string()),
  kb_sources: z.array(z.string()),
  coverage: z.object({ human: z.string(), ai: z.string() }),
});

export const ContentSystemSchema = z.object({
  priority_types: z.array(z.string()),
  target_monthly_volume: z.record(z.string(), z.number().int().nonnegative()).optional(),
  channels: z.array(z.string()),
  voice_risk: z.number().int().min(0).max(10),
  approval_flow: z.string(),
  brand_sources: z.array(z.string()),
});

export const DataBiSystemSchema = z.object({
  metrics: z.array(z.string()),
  sources: z.array(z.string()),
  reporting_cadence: z.string(),
  nlq_examples: z.array(z.string()),
  data_quality: z.number().int().min(1).max(5),
});

export const WorkflowFlowSchema = z.object({
  name: z.string(),
  tools: z.array(z.string()),
  manual_steps: z.array(z.string()),
  do_not_automate: z.array(z.string()),
});

export const WorkflowSystemSchema = z.object({
  target_departments: z.array(z.string()),
  flows: z.array(WorkflowFlowSchema),
});

export const VoiceSystemSchema = z.object({
  daily_calls: z.number().int().nonnegative(),
  call_types: z.array(z.string()),
  objectives: z.array(z.string()),
  booking_method: z.string(),
  greeting: z.string(),
  tone: z.string(),
  escalation_rules: z.array(z.string()),
});

export const ConstraintsSchema = z.object({
  compliance: z.array(z.string()),
  data_sensitivity: z.array(z.string()),
});

export const BudgetSchema = z.object({
  monthly_range: z.enum(['<$1k', '$1–3k', '$3–7k', '$7k+']),
  phased_rollout_preference: z.enum(['start_small', 'fully_designed']),
});

export const ClientConfigSchema = z.object({
  company_profile: CompanyProfileSchema,
  stack: StackSchema,
  support_system: SupportSystemSchema.optional(),
  content_system: ContentSystemSchema.optional(),
  data_bi_system: DataBiSystemSchema.optional(),
  workflow_system: WorkflowSystemSchema.optional(),
  voice_system: VoiceSystemSchema.optional(),
  constraints: ConstraintsSchema,
  budget: BudgetSchema,
  priorities: z.array(z.string()),
});

export type ClientConfig = z.infer<typeof ClientConfigSchema>;

export default ClientConfigSchema;
