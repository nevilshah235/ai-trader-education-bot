import { serve } from '@hono/node-server';
import { Hono } from 'hono';
import type { EducationFeedbackRequest, EducationFeedbackResponse } from '@ai-edu/shared';

const app = new Hono();

app.post('/api/education/feedback', async (c) => {
  const body = await c.req.json<EducationFeedbackRequest>();
  // Stub: later wire to Analyst/Tutor agents, RAG, DB
  const response: EducationFeedbackResponse = {
    version: 1,
    trade_explanation: 'Stub explanation',
    learning_recommendation: 'Stub recommendation',
  };
  return c.json(response);
});

const port = Number(process.env.PORT) || 3000;
serve({ fetch: app.fetch, port }, (info) => {
  console.log(`Server listening on http://localhost:${info.port}`);
});
