import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { EvaluationResult, ScenarioInfo, PersonalityInfo } from '@/types'
import { createEvaluation, getEvaluation, getEvaluations, getScenarios, getPersonalities } from '@/services/api'

export const useEvaluationStore = defineStore('evaluation', () => {
  const currentTask = ref<EvaluationResult | null>(null)
  const evaluationHistory = ref<EvaluationResult[]>([])
  const scenarios = ref<ScenarioInfo[]>([])
  const personalities = ref<PersonalityInfo[]>([])
  const isLoading = ref(false)
  const isEvaluating = ref(false)

  async function loadScenarios() {
    scenarios.value = await getScenarios()
  }

  async function loadPersonalities() {
    personalities.value = await getPersonalities()
  }

  async function startEvaluation(scenario: string, personality: string) {
    console.log('[DEBUG store] startEvaluation | 开始创建任务 | scenario:', scenario, '| personality:', personality)
    isEvaluating.value = true
    currentTask.value = await createEvaluation({ scenario, personality })
    console.log('[DEBUG store] startEvaluation | 任务创建完成 | id:', currentTask.value?.id, '| status:', currentTask.value?.status)
  }

  async function pollEvaluation(taskId: string): Promise<EvaluationResult> {
    console.log('[DEBUG store] pollEvaluation | 轮询任务状态 | taskId:', taskId)
    const result = await getEvaluation(taskId)
    console.log('[DEBUG store] pollEvaluation | 获取结果 | status:', result.status, '| overall_score:', result.overall_score, '| dialogue_history length:', result.dialogue_history?.length ?? 0)
    currentTask.value = result
    return result
  }

  async function loadHistory(scenario?: string, name?: string) {
    isLoading.value = true
    evaluationHistory.value = await getEvaluations(scenario, name)
    isLoading.value = false
  }

  const currentScenarioName = computed(() => {
    if (!currentTask.value) return ''
    return scenarios.value.find(s => s.key === currentTask.value?.scenario)?.name || ''
  })

  const currentPersonalityName = computed(() => {
    if (!currentTask.value) return ''
    return personalities.value.find(p => p.key === currentTask.value?.personality)?.name || ''
  })

  return {
    currentTask,
    evaluationHistory,
    scenarios,
    personalities,
    isLoading,
    isEvaluating,
    currentScenarioName,
    currentPersonalityName,
    loadScenarios,
    loadPersonalities,
    startEvaluation,
    pollEvaluation,
    loadHistory
  }
})