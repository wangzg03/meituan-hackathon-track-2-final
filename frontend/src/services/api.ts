import axios from 'axios'
import type { EvaluationResult, EvaluationRequest, ScenarioInfo, PersonalityInfo } from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

export interface DialogueData {
  turn: number
  model: string
  user: string
}

export async function getDialogue(taskId: string): Promise<{ dialogue: DialogueData[] }> {
  console.log('[DEBUG api] getDialogue | 请求对话 | taskId:', taskId)
  const response = await api.get(`/evaluation/${taskId}/dialogue`)
  console.log('[DEBUG api] getDialogue | 响应 | taskId:', taskId, '| dialogue count:', response.data?.dialogue?.length ?? 0)
  return response.data
}

export async function createEvaluation(request: EvaluationRequest): Promise<EvaluationResult> {
  console.log('[DEBUG api] createEvaluation | 创建任务 | request:', JSON.stringify(request))
  const response = await api.post('/evaluation', request)
  console.log('[DEBUG api] createEvaluation | 响应 | id:', response.data?.id, '| status:', response.data?.status)
  return response.data
}

export async function getEvaluation(taskId: string): Promise<EvaluationResult> {
  console.log('[DEBUG api] getEvaluation | 获取任务 | taskId:', taskId)
  const response = await api.get(`/evaluation/${taskId}`)
  console.log('[DEBUG api] getEvaluation | 响应 | taskId:', taskId, '| status:', response.data?.status, '| overall_score:', response.data?.overall_score)
  return response.data
}

export async function getEvaluations(scenario?: string, name?: string): Promise<EvaluationResult[]> {
  const params: Record<string, string> = {}
  if (scenario) params.scenario = scenario
  if (name) params.name = name
  const response = await api.get('/evaluation', { params })
  return response.data
}

export async function downloadReport(taskId: string): Promise<void> {
  const response = await api.get(`/evaluation/${taskId}/download`, {
    responseType: 'blob'
  })

  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `report_${taskId}.json`)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function getScenarios(): Promise<ScenarioInfo[]> {
  const response = await api.get('/scenarios')
  return response.data
}

export async function getPersonalities(): Promise<PersonalityInfo[]> {
  const response = await api.get('/scenarios/personalities')
  return response.data
}