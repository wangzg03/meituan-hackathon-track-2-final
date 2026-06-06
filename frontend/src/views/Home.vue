<template>
  <div class="home-container">
    <div class="header">
      <div class="logo-section">
        <div class="logo">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="64" height="64" rx="12" fill="#4080FF"/>
            <path d="M20 32h8v8h8v-8h8v-8h-8v-8h-8v8h-8v8z" fill="white"/>
          </svg>
        </div>
        <h1 class="title">对话评测系统</h1>
        <p class="subtitle">自动化对话模型指令遵循能力评估平台</p>
      </div>
    </div>
    
    <div class="features">
      <div class="feature-card">
        <div class="feature-icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <circle cx="24" cy="24" r="20" fill="#E8F0FE"/>
            <path d="M16 24h8v8h8v-8h8v-8h-8v-8h-8v8h-8v8z" fill="#4080FF"/>
          </svg>
        </div>
        <h3>智能测评</h3>
        <p>自动模拟用户与客服对话，评估模型指令遵循能力</p>
      </div>
      
      <div class="feature-card">
        <div class="feature-icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <circle cx="24" cy="24" r="20" fill="#FEF3E2"/>
            <path d="M24 12v24M14 24h20" stroke="#FF9F43" stroke-width="4" stroke-linecap="round"/>
          </svg>
        </div>
        <h3>可解释评估</h3>
        <p>提供详细的评估维度和改进建议，助力模型优化</p>
      </div>
      
      <div class="feature-card">
        <div class="feature-icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <circle cx="24" cy="24" r="20" fill="#E3F2FD"/>
            <path d="M12 24h24M24 12v24" stroke="#2196F3" stroke-width="4" stroke-linecap="round"/>
          </svg>
        </div>
        <h3>可视化报告</h3>
        <p>图表化展示测评结果，支持报告下载和历史记录查询</p>
      </div>
    </div>
    
    <div class="actions">
      <el-button type="primary" size="large" @click="$router.push('/evaluation')">
        开始测评
      </el-button>
      <el-button size="large" @click="$router.push('/records')">
        查看记录
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.header {
  text-align: center;
  margin-bottom: 60px;
}

.logo-section {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.logo {
  margin-bottom: 20px;
}

.title {
  font-size: 48px;
  font-weight: 700;
  color: white;
  margin: 0 0 12px 0;
}

.subtitle {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
}

.features {
  display: flex;
  gap: 30px;
  margin-bottom: 60px;
  flex-wrap: wrap;
  justify-content: center;
}

.feature-card {
  background: white;
  border-radius: 16px;
  padding: 30px;
  width: 280px;
  text-align: center;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.feature-icon {
  margin-bottom: 20px;
}

.feature-card h3 {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin: 0 0 10px 0;
}

.feature-card p {
  font-size: 14px;
  color: #666;
  margin: 0;
  line-height: 1.6;
}

.actions {
  display: flex;
  gap: 20px;
}

.actions .el-button {
  padding: 14px 40px;
  font-size: 16px;
  border-radius: 30px;
}

.actions .el-button--primary {
  background: white;
  color: #667eea;
  border: none;
}

.actions .el-button--primary:hover {
  background: rgba(255, 255, 255, 0.9);
}

.actions .el-button:not(.el-button--primary) {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
}

.actions .el-button:not(.el-button--primary):hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>