/* types.ts — shared TypeScript types */

export interface ProfileData {
  name: string
  experience_level: 'Fresher' | 'Mid' | 'Senior'
  job_role: string
  skills: string[]
}

export interface QuestionItem {
  question: string
  model_answer: string
  tip: string
}

export interface ReadinessAssessment {
  score: number
  recommendations: string[]
}

export interface GenerateResponse {
  technical: QuestionItem[]
  behavioral: QuestionItem[]
  readiness: ReadinessAssessment
}
