import { z } from 'zod';

export const IntakeFormSchema = z.object({
  company_name: z.string().optional(),
  website: z.string().optional().refine(v => !v || /^https?:\/\//.test(v), { message: 'must be a valid url' }),
  industry: z.string().optional(),
  size: z.string().optional(),
  business_model: z.string().optional(),
  objectives: z.array(z.string()).optional(),
  urgency: z.string().optional(),
  website_platform: z.string().optional(),
  crm: z.string().optional(),
  helpdesk: z.string().optional(),
  email: z.string().optional(),
  comms_tools: z.string().optional(),
  telephony: z.string().optional(),
  calendar: z.string().optional(),
  support_system: z.string().optional(),
  content_system: z.string().optional(),
  data_bi_system: z.string().optional(),
  workflow_system: z.string().optional(),
  voice_system: z.string().optional(),
  constraints: z.string().optional(),
  budget_monthly_range: z.enum(['<$1k', '$1–3k', '$3–7k', '$7k+']).optional(),
  budget_phased_preference: z.enum(['start_small', 'fully_designed']).optional(),
});

export type IntakeFormValues = z.infer<typeof IntakeFormSchema>;

export default IntakeFormSchema;
