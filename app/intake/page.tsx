'use client';
import React from 'react';
import IntakeForm from './components/IntakeForm';

export default function IntakePage() {
  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', padding: '1rem' }}>
      <h1>Agency Intake Form</h1>
      <p>Please provide details about your company and objectives.</p>
      <IntakeForm />
    </div>
  );
}
