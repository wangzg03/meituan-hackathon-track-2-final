export interface DialogueTurn {
  model: string
  user: string
}

export interface EvaluationResult {
  id: string
  name: string
  scenario: string
  personality: string
  status: 'running' | 'completed' | 'failed'
  overall_score: number
  readiness_score: number
  readiness_comment: string
  scores: {
    task_completion?: number
    process_adherence?: number
    constraint_compliance?: number
    naturalness?: number
    strategy_adaptation?: number
  }
  strengths: string[]
  weaknesses: Array<{
    dimension: string
    turn: number
    quote: string
    reason: string
    suggestion: string
  }>
  critical_incidents: Array<{
    turn: number
    type: string
    robot_response: string
    evaluation: string
  }>
  improvement_suggestions: string[]
  dialogue_history: DialogueTurn[]
  created_at: string
  // 新增功能验证字段
  functional_validation?: {
    passed_steps: string[]
    failed_steps: string[]
    step_details: Record<string, { passed: boolean; evidence: string }>
    overall_functional_score: number
    completion_rate: number
  }
}

export interface EvaluationRequest {
  scenario: string
  personality: string
}

export interface ScenarioInfo {
  key: string
  name: string
  description: string
}

export interface PersonalityInfo {
  key: string
  name: string
}