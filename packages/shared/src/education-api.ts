/**
 * Intelligence Layer API request/response types
 */

import type { LearningPayload } from './learning-payload';

export type EducationFeedbackRequest = LearningPayload;

export interface EducationFeedbackResponse {
  version: number;
  trade_explanation?: string;
  learning_recommendation?: string;
  run_summary?: string;
}
