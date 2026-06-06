<template>
  <div class="records-container">
    <Layout>
      <div class="records-content">
        <div class="search-section">
          <el-form :model="searchForm" inline class="search-form">
            <el-form-item label="任务名称">
              <el-input v-model="searchForm.name" placeholder="输入任务名称搜索" clearable style="width: 280px" @keyup.enter="handleSearch" />
            </el-form-item>
            <el-form-item label="场景类型">
              <el-select v-model="searchForm.scenario" placeholder="全部" clearable>
                <el-option v-for="scenario in scenarios" :key="scenario.key" :label="scenario.name" :value="scenario.key" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSearch">查询</el-button>
              <el-button @click="handleReset">重置</el-button>
            </el-form-item>
          </el-form>
        </div>

        <div class="table-section">
          <el-table :data="evaluationHistory" :loading="isLoading" border style="width: 100%">
            <el-table-column prop="name" label="任务名称" min-width="260" show-overflow-tooltip />
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="scope">
                {{ formatDateTime(scope.row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag :type="getStatusType(scope.row.status)">{{ getStatusText(scope.row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="overall_score" label="综合得分" width="100">
              <template #default="scope">
                <span :class="getScoreClass(scope.row.overall_score)">{{ scope.row.overall_score.toFixed(1) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="readiness_score" label="就绪度" width="100">
              <template #default="scope">
                <span :class="getScoreClass(scope.row.readiness_score)">{{ scope.row.readiness_score.toFixed(1) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="scope">
                <el-button size="small" type="primary" @click="handleDownload(scope.row.id)" :disabled="scope.row.status !== 'completed'">
                  下载报告
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <el-dialog title="测评详情" :visible.sync="detailVisible" width="800px">
          <div v-if="selectedEvaluation" class="detail-content">
            <div class="detail-header">
              <div class="detail-info">
                <p><strong>任务名称:</strong> {{ selectedEvaluation.name }}</p>
                <p><strong>场景:</strong> {{ getScenarioName(selectedEvaluation.scenario) }}</p>
                <p><strong>性格:</strong> {{ getPersonalityName(selectedEvaluation.personality) }}</p>
                <p><strong>状态:</strong> <el-tag :type="getStatusType(selectedEvaluation.status)">{{ getStatusText(selectedEvaluation.status) }}</el-tag></p>
                <p><strong>创建时间:</strong> {{ formatDateTime(selectedEvaluation.created_at) }}</p>
              </div>
              <div class="detail-scores">
                <div class="score-item">
                  <span class="score-num">{{ selectedEvaluation.overall_score.toFixed(1) }}</span>
                  <span class="score-name">综合得分</span>
                </div>
                <div class="score-item">
                  <span class="score-num">{{ selectedEvaluation.readiness_score.toFixed(1) }}</span>
                  <span class="score-name">就绪度</span>
                </div>
              </div>
            </div>

            <div class="detail-section">
              <h3>对话记录</h3>
              <div class="dialogue-list">
                <div v-for="(turn, index) in selectedEvaluation.dialogue_history" :key="index" class="dialogue-item">
                  <span class="turn-num">第{{ index + 1 }}轮</span>
                  <div class="dialogue-content">
                    <p><strong>客服:</strong> {{ turn.model }}</p>
                    <p><strong>用户:</strong> {{ turn.user }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-dialog>
      </div>
    </Layout>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useEvaluationStore } from '@/stores/evaluation'
import { downloadReport } from '@/services/api'
import type { EvaluationResult, ScenarioInfo } from '@/types'
import Layout from '@/components/Layout.vue'

const store = useEvaluationStore()
const { evaluationHistory, isLoading } = storeToRefs(store)

const searchForm = ref<{ name: string; scenario: string }>({
  name: '',
  scenario: ''
})

const detailVisible = ref(false)
const selectedEvaluation = ref<EvaluationResult | null>(null)

const scenarios = ref<ScenarioInfo[]>([])

onMounted(async () => {
  await store.loadScenarios()
  await store.loadPersonalities()
  scenarios.value = store.scenarios
  await store.loadHistory()
})

function handleSearch() {
  store.loadHistory(searchForm.value.scenario || undefined, searchForm.value.name || undefined)
}

function handleReset() {
  searchForm.value = { name: '', scenario: '' }
  store.loadHistory()
}

function handleViewDetail(evaluation: EvaluationResult) {
  selectedEvaluation.value = evaluation
  detailVisible.value = true
}

async function handleDownload(taskId: string) {
  await downloadReport(taskId)
}

function formatDateTime(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

function getScenarioName(key: string): string {
  return scenarios.value.find(s => s.key === key)?.name || key
}

function getPersonalityName(key: string): string {
  return store.personalities.find(p => p.key === key)?.name || key
}

function getStatusType(status: string): string {
  switch (status) {
    case 'completed': return 'success'
    case 'running': return 'warning'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

function getStatusText(status: string): string {
  switch (status) {
    case 'completed': return '已完成'
    case 'running': return '进行中'
    case 'failed': return '失败'
    default: return status
  }
}

function getScoreClass(score: number): string {
  if (score >= 80) return 'score-high'
  if (score >= 60) return 'score-medium'
  return 'score-low'
}
</script>

<style scoped>
.records-container {
  min-height: calc(100vh - 64px);
}

.records-content {
  padding: 24px;
  width: 100%;
  box-sizing: border-box;
}

.search-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.search-form {
  display: flex;
  align-items: center;
  gap: 20px;
}

.table-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.score-high {
  color: #67c23a;
  font-weight: 600;
}

.score-medium {
  color: #e6a23c;
  font-weight: 600;
}

.score-low {
  color: #f56c6c;
  font-weight: 600;
}

.detail-content {
  max-height: 600px;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #eee;
}

.detail-info p {
  margin: 4px 0;
  color: #666;
}

.detail-scores {
  display: flex;
  gap: 30px;
}

.score-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.score-num {
  font-size: 32px;
  font-weight: 700;
  color: #667eea;
}

.score-name {
  font-size: 14px;
  color: #999;
}

.detail-section {
  margin-top: 20px;
}

.detail-section h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px 0;
  color: #333;
}

.dialogue-list {
  max-height: 400px;
  overflow-y: auto;
}

.dialogue-item {
  margin-bottom: 16px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}

.turn-num {
  font-size: 12px;
  color: #999;
  margin-right: 12px;
}

.dialogue-content p {
  margin: 4px 0;
  color: #333;
  font-size: 14px;
}
</style>