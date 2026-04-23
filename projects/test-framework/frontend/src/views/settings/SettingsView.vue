<template>
  <div class="settings-view">
    <el-tabs v-model="activeTab" class="settings-tabs">
      <!-- 通知设置 -->
      <el-tab-pane label="通知设置" name="notify">
        <el-card shadow="never" style="max-width: 700px">
          <template #header>
            <div class="card-header">
              <span>飞书通知配置</span>
              <el-button size="small" type="primary" @click="saveNotifySettings" :loading="saving">
                保存配置
              </el-button>
            </div>
          </template>

          <el-form label-width="140px" label-position="left">
            <el-form-item label="飞书 Webhook">
              <el-input
                v-model="notifyForm.feishu_webhook"
                placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx"
                clearable
              />
            </el-form-item>

            <el-form-item label="执行完成通知">
              <el-switch v-model="notifyForm.notify_on_completion" />
              <div class="field-hint">开启后，测试用例执行完成会自动发送飞书通知</div>
            </el-form-item>

            <el-divider />

            <el-form-item label="测试通知">
              <el-button @click="sendTestNotify" :loading="testingNotify" size="small">
                发送测试消息
              </el-button>
              <span class="field-hint" style="margin-left: 12px">向飞书群发送一条测试消息，验证配置是否正确</span>
            </el-form-item>

            <el-alert v-if="notifyStatus.message" :type="notifyStatus.type" show-icon style="margin-top: 12px">
              {{ notifyStatus.message }}
            </el-alert>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 关于 -->
      <el-tab-pane label="关于" name="about">
        <el-card shadow="never" style="max-width: 700px">
          <el-descriptions title="Test Framework" :column="2" border>
            <el-descriptions-item label="版本">1.0.0</el-descriptions-item>
            <el-descriptions-item label="技术栈">Python + FastAPI + Vue3</el-descriptions-item>
            <el-descriptions-item label="自动化">Playwright</el-descriptions-item>
            <el-descriptions-item label="数据存储">SQLite</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { settingsApi } from '@/api'

const activeTab = ref('notify')
const saving = ref(false)
const testingNotify = ref(false)
const notifyStatus = reactive({ message: '', type: 'success' })

const notifyForm = reactive({
  feishu_webhook: '',
  notify_on_completion: false,
})

async function loadSettings() {
  try {
    const data = await settingsApi.getNotify()
    notifyForm.feishu_webhook = data.feishu_webhook || ''
    notifyForm.notify_on_completion = data.notify_on_completion || false
  } catch (e) {
    console.error('加载设置失败', e)
  }
}

async function saveNotifySettings() {
  saving.value = true
  try {
    await settingsApi.saveNotify({
      feishu_webhook: notifyForm.feishu_webhook,
      notify_on_completion: notifyForm.notify_on_completion,
    })
    ElMessage.success('配置已保存')
    notifyStatus.message = ''
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function sendTestNotify() {
  if (!notifyForm.feishu_webhook) {
    ElMessage.warning('请先填写 Webhook 地址')
    return
  }
  testingNotify.value = true
  notifyStatus.message = ''
  try {
    await settingsApi.testNotify({ feishu_webhook: notifyForm.feishu_webhook })
    notifyStatus.message = '测试消息发送成功！'
    notifyStatus.type = 'success'
    ElMessage.success('测试消息发送成功')
  } catch (e) {
    notifyStatus.message = '发送失败，请检查 Webhook 地址是否正确'
    notifyStatus.type = 'error'
    ElMessage.error('发送失败')
  } finally {
    testingNotify.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.field-hint {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
  margin-top: 2px;
}
</style>
