'use client';
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import IntakeFormSchema, { IntakeFormValues } from '../../../src/validation/intakeForm';

const objectiveOptions = ['support', 'content', 'data', 'workflow', 'voice'];

export default function IntakeForm() {
  const { register, handleSubmit, watch } = useForm<IntakeFormValues>({
    resolver: zodResolver(IntakeFormSchema),
    defaultValues: { objectives: [] },
  });
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const objectives = watch('objectives') || [];

  const onSubmit = async (values: IntakeFormValues) => {
    setSubmitting(true);
    try {
      const payload: any = {
        company_profile: {
          name: values.company_name,
          website: values.website,
          industry: values.industry,
          size: values.size,
          business_model: values.business_model,
          objectives: values.objectives || [],
          urgency: values.urgency,
        },
        stack: {
          website_platform: values.website_platform,
          crm: values.crm,
          helpdesk: values.helpdesk,
          email: values.email,
          comms_tools: values.comms_tools ? values.comms_tools.split(',').map(s => s.trim()) : [],
          telephony: values.telephony,
          calendar: values.calendar,
        },
        // optional systems: parsed from JSON textarea if provided
        support_system: safeJson(values.support_system),
        content_system: safeJson(values.content_system),
        data_bi_system: safeJson(values.data_bi_system),
        workflow_system: safeJson(values.workflow_system),
        voice_system: safeJson(values.voice_system),
        constraints: safeJson(values.constraints) || { compliance: [], data_sensitivity: [] },
        budget: {
          monthly_range: values.budget_monthly_range || '<$1k',
          phased_rollout_preference: values.budget_phased_preference || 'start_small',
        },
      };

      const res = await fetch('/api/intake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (res.ok) {
        alert('Submitted — normalized config saved. Submission id: ' + data.submissionId);
        setStep(0);
      } else {
        alert('Error: ' + (data.error || 'unknown'));
      }
    } catch (err: any) {
      alert('Submit failed: ' + String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {step === 0 && (
        <section>
          <h2>Company Profile</h2>
          <label>Company name</label>
          <input {...register('company_name')} />
          <label>Website</label>
          <input {...register('website')} />
          <label>Industry</label>
          <input {...register('industry')} />
          <label>Company size</label>
          <input {...register('size')} />
          <label>Business model</label>
          <input {...register('business_model')} />
          <label>Urgency / timeline</label>
          <input {...register('urgency')} />
          <div style={{ marginTop: 8 }}>
            <button type="button" onClick={() => setStep(1)}>Next</button>
          </div>
        </section>
      )}

      {step === 1 && (
        <section>
          <h2>Tech Stack & Integrations</h2>
          <label>Website platform</label>
          <input {...register('website_platform')} />
          <label>CRM</label>
          <input {...register('crm')} />
          <label>Helpdesk</label>
          <input {...register('helpdesk')} />
          <label>Primary email</label>
          <input {...register('email')} />
          <label>Comms tools (comma separated)</label>
          <input {...register('comms_tools')} />
          <label>Telephony</label>
          <input {...register('telephony')} />
          <label>Calendar</label>
          <input {...register('calendar')} />
          <div style={{ marginTop: 8 }}>
            <button type="button" onClick={() => setStep(0)}>Back</button>
            <button type="button" onClick={() => setStep(2)}>Next</button>
          </div>
        </section>
      )}

      {step === 2 && (
        <section>
          <h2>Objectives & Priorities</h2>
          <p>Select your main objectives (order doesn't matter)</p>
          {objectiveOptions.map(opt => (
            <label key={opt} style={{ display: 'block' }}>
              <input type="checkbox" value={opt} {...register('objectives')} /> {opt}
            </label>
          ))}
          <div style={{ marginTop: 8 }}>
            <button type="button" onClick={() => setStep(1)}>Back</button>
            <button type="button" onClick={() => setStep(3)}>Next</button>
          </div>
        </section>
      )}

      {step === 3 && (
        <section>
          <h2>Optional Systems (advanced)</h2>
          <p>Paste JSON for any advanced system or leave blank to use defaults.</p>
          <label>Support system (JSON)</label>
          <textarea rows={4} {...register('support_system')} />
          <label>Content system (JSON)</label>
          <textarea rows={4} {...register('content_system')} />
          <label>Data & BI system (JSON)</label>
          <textarea rows={4} {...register('data_bi_system')} />
          <label>Workflow system (JSON)</label>
          <textarea rows={4} {...register('workflow_system')} />
          <label>Voice system (JSON)</label>
          <textarea rows={4} {...register('voice_system')} />
          <div style={{ marginTop: 8 }}>
            <button type="button" onClick={() => setStep(2)}>Back</button>
            <button type="button" onClick={() => setStep(4)}>Next</button>
          </div>
        </section>
      )}

      {step === 4 && (
        <section>
          <h2>Constraints & Budget</h2>
          <label>Constraints (JSON: {`{ compliance: [], data_sensitivity: [] }`})</label>
          <textarea rows={3} {...register('constraints')} />
          <label>Budget range</label>
          <select {...register('budget_monthly_range')}>
            <option value="<$1k">&lt;$1k</option>
            <option value="$1–3k">$1–3k</option>
            <option value="$3–7k">$3–7k</option>
            <option value="$7k+">$7k+</option>
          </select>
          <label>Phased rollout preference</label>
          <select {...register('budget_phased_preference')}>
            <option value="start_small">Start small</option>
            <option value="fully_designed">Fully designed</option>
          </select>
          <div style={{ marginTop: 8 }}>
            <button type="button" onClick={() => setStep(3)}>Back</button>
            <button type="submit" disabled={submitting}>{submitting ? 'Submitting…' : 'Submit'}</button>
          </div>
        </section>
      )}
    </form>
  );
}

function safeJson(value?: string) {
  if (!value) return undefined;
  try {
    return JSON.parse(value);
  } catch (err) {
    // try to interpret as simple comma lists or fallback to raw string
    const asComma = value.split(',').map(s => s.trim()).filter(Boolean);
    if (asComma.length > 0) return asComma;
    return undefined;
  }
}
