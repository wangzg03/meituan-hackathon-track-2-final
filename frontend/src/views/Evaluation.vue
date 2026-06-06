<template>
  <div class="evaluation-container">
    <Layout>
      <div class="evaluation-content">
        <div class="section">
          <h2 class="section-title">创建测评任务</h2>
          <el-form :model="formData" class="task-form">
            <el-form-item label="场景类型">
              <el-select v-model="formData.scenario" placeholder="请选择场景类型">
                <el-option v-for="scenario in scenarios" :key="scenario.key" :label="scenario.name" :value="scenario.key" />
              </el-select>
            </el-form-item>
            <el-form-item label="用户性格">
              <el-select v-model="formData.personality" placeholder="请选择用户性格类型">
                <el-option v-for="personality in personalities" :key="personality.key" :label="personality.name" :value="personality.key" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <div class="button-group">
                <div class="top-row">
                  <StartEvaluationButton 
                    :disabled="isEvaluating || !formData.scenario || !formData.personality"
                    :loading="isEvaluating"
                    loading-text="测评中..."
                    @click="handleStartEvaluation" 
                  />
                  <TaskStatusInput :status="taskStatus" />
                </div>
                <PreviewButton @click="setMockData" />
              </div>
            </el-form-item>
          </el-form>
        </div>

        <div class="section">
          <h2 class="section-title">对话过程</h2>
          <div class="dialogue-container">
            <div v-if="!currentTask" class="empty-dialogue">
              <p>请先创建测评任务开始对话</p>
            </div>
            <div v-else ref="dialogueContainerRef" class="dialogue-content">
              <div v-if="currentTask.status === 'running'" class="running-indicator">
                <el-progress type="circle" :percentage="progressPercentage" :width="60" />
                <p>正在进行对话测评...</p>
              </div>
              <!-- 显示流式对话 -->
              <template v-if="currentTask.status === 'running'">
              <div v-for="(turn, index) in streamingDialogues" :key="`stream-${index}`" 
                   class="dialogue-turn animate-fade-in">
                <div class="robot-message">
                  <div class="avatar robot">🤖</div>
                  <div class="message-content">
                    <span class="label">客服智能体</span>
                    <p>{{ turn.model }}</p>
                  </div>
                </div>
                <div class="user-message">
                  <div class="avatar user">👤</div>
                  <div class="message-content">
                    <span class="label">用户智能体</span>
                    <p>{{ turn.user }}</p>
                  </div>
                </div>
              </div>
              </template>
              <!-- 任务完成后显示完整对话历史 -->
              <template v-if="currentTask.status !== 'running' && currentTask.dialogue_history.length > 0">
                <div v-for="(turn, index) in currentTask.dialogue_history" :key="`history-${index}`" 
                     class="dialogue-turn"
                     :class="{ 'animate-fade-in': streamingDialogues.length === 0 }">
                  <div class="robot-message">
                    <div class="avatar robot">🤖</div>
                    <div class="message-content">
                      <span class="label">客服智能体</span>
                      <p>{{ turn.model }}</p>
                    </div>
                  </div>
                  <div class="user-message">
                    <div class="avatar user">👤</div>
                    <div class="message-content">
                      <span class="label">用户智能体</span>
                      <p>{{ turn.user }}</p>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </div>

        <div class="section">
          <h2 class="section-title">测评结果</h2>
          <div class="result-container">
            <!-- 任务失败时显示错误信息 -->
            <div v-if="currentTask && currentTask.status === 'failed'" class="failed-result">
              <div class="failed-icon">⚠️</div>
              <p class="failed-title">评估任务失败</p>
              <p class="failed-message">{{ currentTask.readiness_comment || '未知错误' }}</p>
              <p class="failed-hint" v-if="currentTask.dialogue_history && currentTask.dialogue_history.length > 0">
                已生成 {{ currentTask.dialogue_history.length }} 轮对话，可在上方"对话过程"区域查看
              </p>
            </div>
            <!-- 无任务或运行中时显示空状态 -->
            <div v-else-if="!currentTask || currentTask.status === 'running'" class="empty-result">
              <div class="empty-icon">📊</div>
              <p>暂无测评结果</p>
              <p class="empty-hint">请创建测评任务并完成测评后查看结果</p>
            </div>
            <template v-else-if="currentTask && currentTask.status === 'completed'">
              <div class="score-summary">
                <div class="score-card">
                  <div class="score-circle">
                    <span class="score-value">{{ (currentTask.overall_score ?? 0).toFixed(1) }}</span>
                    <span class="score-label">综合得分</span>
                  </div>
                </div>
                <div class="score-card">
                  <div class="score-circle readiness">
                    <span class="score-value">{{ (currentTask.readiness_score ?? 0).toFixed(1) }}</span>
                    <span class="score-label">就绪度</span>
                  </div>
                </div>
                <div class="score-card" v-if="currentTask.functional_validation">
                  <div class="score-circle functional">
                    <span class="score-value">{{ ((currentTask.functional_validation.completion_rate ?? 0) * 100).toFixed(0) }}</span>
                    <span class="score-label">功能完成率</span>
                  </div>
                </div>
              </div>

              <div class="chart-section">
                <ScoreChart :scores="currentTask.scores" />
              </div>

              <!-- 新增功能验证结果展示 -->
              <div class="functional-section" v-if="currentTask.functional_validation">
                <h3 class="subsection-title">功能步骤完成情况</h3>
                <div class="functional-steps">
                  <div class="steps-header">
                    <span>步骤名称</span>
                    <span>状态</span>
                    <span>证据</span>
                  </div>
                  <div v-for="(detail, step) in currentTask.functional_validation.step_details" :key="step" 
                       class="step-row" :class="{ passed: detail.passed, failed: !detail.passed }">
                    <span class="step-name">{{ step }}</span>
                    <span class="step-status">
                      <el-tag :type="detail.passed ? 'success' : 'danger'">
                        {{ detail.passed ? '已完成' : '未完成' }}
                      </el-tag>
                    </span>
                    <span class="step-evidence">{{ detail.evidence || '-' }}</span>
                  </div>
                </div>
                <div class="functional-summary">
                  <p>已完成步骤: {{ currentTask.functional_validation.passed_steps?.length ?? 0 }} / {{ Object.keys(currentTask.functional_validation.step_details ?? {}).length }}</p>
                  <p>完成率: {{ ((currentTask.functional_validation.completion_rate ?? 0) * 100).toFixed(1) }}</p>
                </div>
              </div>

              <div class="details-section">
                <div class="detail-card">
                  <h3>优势亮点</h3>
                  <ul v-if="(currentTask.strengths?.length ?? 0) > 0">
                    <li v-for="(item, index) in currentTask.strengths" :key="index">{{ item }}</li>
                  </ul>
                  <p v-else class="empty-text">暂无</p>
                </div>
                <div class="detail-card">
                  <h3>问题与改进建议</h3>
                  <div v-if="(currentTask.weaknesses?.length ?? 0) > 0">
                    <div v-for="(item, index) in currentTask.weaknesses" :key="index" class="weakness-item">
                      <p><strong>问题语句:</strong> "{{ item.quote }}"</p>
                      <p><strong>原因:</strong> {{ item.reason }}</p>
                      <p><strong>建议:</strong> {{ item.suggestion }}</p>
                    </div>
                  </div>
                  <p v-else class="empty-text">暂无</p>
                </div>
                <div class="detail-card">
                  <h3>系统优化建议</h3>
                  <ul v-if="(currentTask.improvement_suggestions?.length ?? 0) > 0">
                    <li v-for="(item, index) in currentTask.improvement_suggestions" :key="index">{{ item }}</li>
                  </ul>
                  <p v-else class="empty-text">暂无</p>
                </div>
              </div>

              <div class="action-section">
                <el-button type="primary" @click="handleDownloadReport">下载测评报告</el-button>
                <el-button @click="handleReset">重新测评</el-button>
              </div>
            </template>
          </div>
        </div>
      </div>
    </Layout>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useEvaluationStore } from '@/stores/evaluation'
import { downloadReport, getDialogue, type DialogueData } from '@/services/api'
import type { ScenarioInfo, PersonalityInfo, EvaluationRequest, DialogueTurn, EvaluationResult } from '@/types'
import Layout from '@/components/Layout.vue'
import ScoreChart from '@/components/ScoreChart.vue'
import StartEvaluationButton from '@/components/StartEvaluationButton.vue'
import PreviewButton from '@/components/PreviewButton.vue'
import TaskStatusInput from '@/components/TaskStatusInput.vue'

const store = useEvaluationStore()
const { currentTask, isEvaluating } = storeToRefs(store)

const formData = ref<EvaluationRequest>({
  scenario: '',
  personality: ''
})

const progressPercentage = ref(0)
const taskStatus = ref('')
// 用于存储实时流式对话
const streamingDialogues = ref<DialogueTurn[]>([])
let pollInterval: number | null = null
const dialogueContainerRef = ref<HTMLElement | null>(null)

const scenarios = ref<ScenarioInfo[]>([])
const personalities = ref<PersonalityInfo[]>([])

// Mock数据用于预览对话效果（开发调试用）- 使用真实测评报告数据
const mockEvaluationData: EvaluationResult = {
  id: 'mock-task-ce460652',
  name: '预览任务-外卖配送场景',
  scenario: 'delivery',
  personality: 'random',
  status: 'completed',
  overall_score: 55.0,
  readiness_score: 60.0,
  readiness_comment: '存在关键信息缺失风险（如未说明连续天数要求），建议补充话术模板后上线，需特别注意用户对任务量的质疑场景',
  scores: {
    task_completion: 60.0,
    process_adherence: 50.0,
    constraint_compliance: 70.0,
    naturalness: 40.0,
    strategy_adaptation: 55.0
  },
  strengths: [
    '在用户犹豫时尝试鼓励（第5轮）',
    '遵守职责外问题处理规范（第3/4轮）'
  ],
  weaknesses: [
    {
      dimension: 'naturalness',
      turn: 2,
      quote: '当日需完成X单，未达标会影响合同与平台派单',
      reason: '未直接回答用户对X的具体数值疑问，机械重复业务指令模板',
      suggestion: '可补充\'具体数量会在APP任务页显示，请登录查看\'等引导性表述'
    }
  ],
  critical_incidents: [
    {
      turn: 4,
      type: '用户拒绝',
      robot_response: '那理解了，你多注意身体，再见',
      evaluation: '处理不当，未执行\'提醒安全\'核心流程，也未强调\'连续完成W天有奖励\'的激励点'
    }
  ],
  improvement_suggestions: [
    '增加对\'X/Y/Z/W具体数值\'的模糊化处理话术训练',
    '强化\'安全提醒\'的固定话术植入'
  ],
  dialogue_history: [
    { model: '王明你好，我是站长，你报名的飞毛腿合同已生效。午晚高峰需上线，单日X单、多日Y单。', user: '具体多少单？\n完不成咋办？' },
    { model: '当日需完成X单，未达标会影响合同与平台派单。', user: 'X是多少？扣钱吗？' },
    { model: '我向同事确认后再回电给你。我现在能回答的先回答。', user: '等一下，我没听清' },
    { model: '我向同事确认后再回电给你。我现在能回答的先回答。', user: '算了，我再想想。' },
    { model: '不想跑我理解，不妨试试，跑单路上一定要注意安全。', user: '你刚说啥？' },
    { model: '那理解了，你多注意身体，再见。', user: '好的，再见。' }
  ],
  created_at: '2026-05-28T20:33:50.181345',
  functional_validation: {
    passed_steps: ['告知合同生效', '挽留或鼓励', '提醒安全', '结束祝福'],
    failed_steps: ['询问是否可以配送', '说明连续Y天要求'],
    step_details: {
      '告知合同生效': {
        passed: true,
        evidence: '王明你好，我是站长，你报名的飞毛腿合同已生效。午晚高峰需上线，单日X单、多日Y单。'
      },
      '询问是否可以配送': {
        passed: false,
        evidence: ''
      },
      '说明连续Y天要求': {
        passed: false,
        evidence: ''
      },
      '挽留或鼓励': {
        passed: true,
        evidence: '不想跑我理解，不妨试试，跑单路上一定要注意安全。'
      },
      '提醒安全': {
        passed: true,
        evidence: '不想跑我理解，不妨试试，跑单路上一定要注意安全。那理解了，你多注意身体，再见。'
      },
      '结束祝福': {
        passed: true,
        evidence: '那理解了，你多注意身体，再见。'
      }
    },
    overall_functional_score: 0.6666666666666666,
    completion_rate: 0.6666666666666666
  }
}

// 设置mock数据预览（开发调试用）
function setMockData() {
  streamingDialogues.value = mockEvaluationData.dialogue_history
  currentTask.value = { ...mockEvaluationData }
}

onMounted(async () => {
  await store.loadScenarios()
  await store.loadPersonalities()
  scenarios.value = store.scenarios
  personalities.value = store.personalities
})

async function handleStartEvaluation() {
  if (!formData.value.scenario || !formData.value.personality) return

  taskStatus.value = '任务创建成功，执行中...'
  progressPercentage.value = 10
  streamingDialogues.value = []

  console.log('[DEBUG] handleStartEvaluation | 开始测评 | scenario:', formData.value.scenario, '| personality:', formData.value.personality)

  try {
    await store.startEvaluation(formData.value.scenario, formData.value.personality)
    console.log('[DEBUG] handleStartEvaluation | 任务创建成功 | currentTask:', JSON.stringify(currentTask.value, null, 2))

    if (currentTask.value) {
      console.log('[DEBUG] handleStartEvaluation | 启动轮询 | taskId:', currentTask.value.id)
      startPolling(currentTask.value.id)
    } else {
      isEvaluating.value = false
      taskStatus.value = '任务创建失败'
    }
  } catch (error) {
    console.error('[DEBUG] handleStartEvaluation | 任务创建失败:', error)
    isEvaluating.value = false
    taskStatus.value = '任务创建失败：' + (error as Error).message
  }
}

function startPolling(taskId: string) {
  console.log('[DEBUG] startPolling | 轮询启动 | taskId:', taskId)
  pollInterval = window.setInterval(async () => {
    let taskCompleted = false

    try {
      const result = await getDialogue(taskId)
      console.log('[DEBUG] startPolling | getDialogue 响应 | taskId:', taskId, '| dialogue count:', result?.dialogue?.length ?? 0)
      if (result && result.dialogue) {
        const newDialogues = result.dialogue as DialogueData[]
        streamingDialogues.value = newDialogues.map(d => ({
          model: d.model,
          user: d.user
        }))

        console.log('[DEBUG] startPolling | 对话更新 | streamingDialogues.length:', streamingDialogues.value.length)
        console.log('[DEBUG] startPolling | 最新对话轮次:', JSON.stringify(newDialogues[newDialogues.length - 1], null, 2))

        progressPercentage.value = Math.min(90, 10 + streamingDialogues.value.length * 15)

        nextTick(() => {
          scrollToBottom()
        })
      }
    } catch (error) {
      console.error('[DEBUG] startPolling | getDialogue 错误:', error)
    }

    try {
      const taskResult = await store.pollEvaluation(taskId)
      console.log('[DEBUG] startPolling | pollEvaluation 响应 | status:', taskResult.status, '| taskId:', taskId)
      if (taskResult.status !== 'running') {
        taskCompleted = true
        console.log('[DEBUG] startPolling | 任务状态变更:', taskResult.status, '| 停止轮询')
        if (pollInterval) {
          clearInterval(pollInterval)
          pollInterval = null
        }
        progressPercentage.value = 100
        taskStatus.value = '任务已完成'
        isEvaluating.value = false
        console.log('[DEBUG] startPolling | 任务完成 | final dialogue_history length:', currentTask.value?.dialogue_history?.length ?? 0)
        console.log('[DEBUG] startPolling | 任务完成 | overall_score:', currentTask.value?.overall_score)
      }
    } catch (error) {
      console.error('[DEBUG] startPolling | pollEvaluation 错误:', error)
    }

    if (taskCompleted && pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }, 1500)
}

function scrollToBottom() {
  if (dialogueContainerRef.value) {
    dialogueContainerRef.value.scrollTop = dialogueContainerRef.value.scrollHeight
  }
}

// 监听 currentTask 变化，重置流式对话
watch(() => currentTask.value, (newTask, oldTask) => {
  console.log('[DEBUG] watch currentTask | 变化检测 | oldTask:', oldTask?.id, '| newTask:', newTask?.id, '| newStatus:', newTask?.status)
  if (!oldTask) return
  if (!newTask || newTask.id !== oldTask?.id) {
    console.log('[DEBUG] watch currentTask | 重置状态 | streamingDialogues 清空')
    streamingDialogues.value = []
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
    isEvaluating.value = false
  }
})

async function handleDownloadReport() {
  if (currentTask.value) {
    await downloadReport(currentTask.value.id)
  }
}

function handleReset() {
  console.log('[DEBUG] handleReset | 重置测评')
  currentTask.value = null
  formData.value = {
    scenario: '',
    personality: ''
  }
  progressPercentage.value = 0
  taskStatus.value = ''
  streamingDialogues.value = []
  isEvaluating.value = false
}
</script>

<style scoped>
.evaluation-container {
  min-height: calc(100vh - 64px);
}

.evaluation-content {
  padding: 24px;
  width: 100%;
  box-sizing: border-box;
}

.section {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin: 0 0 20px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid #eee;
}

.subsection-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 20px 0 15px 0;
}

.task-form {
  max-width: 500px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.task-form .el-form-item {
  margin-bottom: 20px;
  width: 100%;
}

.task-form .el-form-item:last-child {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.button-group {
  display: flex;
  flex-direction: column;
  width: 100%;
  gap: 12px;
  align-items: center;
}

.top-row {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: center;
}

.dialogue-container {
  min-height: 300px;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 20px;
}

.empty-dialogue {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #999;
}

.empty-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #999;
}

.empty-result .empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-result p {
  margin: 8px 0;
  font-size: 14px;
}

.empty-result .empty-hint {
  font-size: 12px;
  color: #ccc;
}

.failed-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
  background-color: #fef0f0;
  border-radius: 8px;
  border: 1px solid #fde2e2;
}

.failed-result .failed-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.failed-result .failed-title {
  font-size: 18px;
  font-weight: 600;
  color: #f56c6c;
  margin: 0 0 12px 0;
}

.failed-result .failed-message {
  font-size: 14px;
  color: #666;
  margin: 0 0 16px 0;
  text-align: center;
  max-width: 600px;
  word-break: break-all;
}

.failed-result .failed-hint {
  font-size: 12px;
  color: #999;
  margin: 0;
}

.dialogue-content {
  max-height: 500px;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.running-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  color: #666;
}

.dialogue-turn {
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.robot-message,
.user-message {
  display: flex;
  gap: 12px;
  margin-bottom: 0;
  width: 100%;
}

.robot-message {
  align-self: flex-start;
  max-width: 80%;
}

.user-message {
  align-self: flex-end;
  max-width: 80%;
  flex-direction: row-reverse;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.avatar.robot {
  background: #e8f0fe;
}

.avatar.user {
  background: #f6ffed;
}

.message-content {
  flex: 1;
}

.message-content .label {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
  display: block;
}

.message-content p {
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 0 12px 12px 12px;
  margin: 0;
  line-height: 1.6;
  color: #333;
  text-align: left;
}

.robot-message .message-content p {
  background: #e8f0fe;
  border-radius: 12px 12px 12px 0;
}

.user-message .message-content {
  text-align: right;
}

.user-message .message-content .label {
  text-align: right;
}

.user-message .message-content p {
  background: #667eea;
  color: white;
  border-radius: 12px 12px 0 12px;
}

.result-container {
  margin-top: 20px;
}

.score-summary {
  display: flex;
  gap: 40px;
  margin-bottom: 30px;
}

.score-card {
  flex: 1;
}

.score-circle {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
}

.score-circle.readiness {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.score-circle.functional {
  background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%);
}

.score-value {
  font-size: 36px;
  font-weight: 700;
}

.score-label {
  font-size: 14px;
  opacity: 0.9;
}

.chart-section {
  margin-bottom: 30px;
}

/* 功能验证区域样式 */
.functional-section {
  background: #fafafa;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 30px;
}

.functional-steps {
  margin-bottom: 15px;
}

.steps-header {
  display: grid;
  grid-template-columns: 1fr 100px 2fr;
  gap: 12px;
  padding: 10px 15px;
  background: #fff;
  border-radius: 6px;
  font-weight: 600;
  font-size: 14px;
  color: #666;
}

.step-row {
  display: grid;
  grid-template-columns: 1fr 100px 2fr;
  gap: 12px;
  padding: 12px 15px;
  background: #fff;
  border-radius: 6px;
  margin-top: 8px;
  align-items: center;
}

.step-row.passed {
  border-left: 4px solid #67c23a;
}

.step-row.failed {
  border-left: 4px solid #f56c6c;
}

.step-name {
  font-weight: 500;
}

.step-evidence {
  font-size: 13px;
  color: #999;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.functional-summary {
  display: flex;
  gap: 20px;
  padding-top: 15px;
  border-top: 1px dashed #ddd;
  font-size: 14px;
  color: #666;
}

.details-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.detail-card {
  background: #fafafa;
  border-radius: 8px;
  padding: 20px;
}

.detail-card h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: #333;
}

.detail-card ul {
  margin: 0;
  padding-left: 20px;
}

.detail-card li {
  margin-bottom: 8px;
  color: #666;
  line-height: 1.6;
}

.empty-text {
  color: #999;
}

.weakness-item {
  background: #fff7e6;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 12px;
}

.weakness-item p {
  margin: 4px 0;
  font-size: 14px;
  color: #666;
}

.action-section {
  display: flex;
  gap: 16px;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}
</style>