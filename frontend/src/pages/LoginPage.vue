<template>
  <div class="login">
    <section class="login-visual">
      <div>
        <div class="eyebrow" style="color: color-mix(in oklch, var(--paper) 74%, transparent)">
          stratum 03 · member ops
        </div>
        <h1>会员<br />分层剖面</h1>
        <p class="caption">
          拾光咖啡 · 8 家门店，600 位会员的 R / F / M 分层。把「一刀切三档」换成本次
          KMeans 剖面：谁在高价值沉睡、谁只等券，一眼看到。
        </p>
      </div>
      <svg viewBox="0 0 620 300" class="login-strata" aria-hidden="true">
        <g opacity="0.9">
          <path d="M0 228 C 150 210, 260 250, 400 232 S 560 208, 620 226 L620 300 L0 300 Z" fill="oklch(0.36 0.05 46)" />
          <path d="M0 186 C 150 166, 280 206, 420 186 S 570 164, 620 182 L620 234 C 520 216, 430 244, 320 232 S 120 214, 0 234 Z" fill="oklch(0.48 0.06 48)" />
          <path d="M0 142 C 160 122, 300 160, 450 140 S 580 122, 620 136 L620 188 C 520 170, 410 200, 300 186 S 120 168, 0 188 Z" fill="oklch(0.6 0.075 56)" />
          <path d="M0 98 C 170 80, 320 118, 470 96 S 590 84, 620 94 L620 144 C 510 128, 400 156, 290 142 S 110 124, 0 146 Z" fill="oklch(0.71 0.085 66)" />
          <path d="M0 54 C 180 38, 340 74, 500 52 S 600 46, 620 50 L620 100 C 520 84, 400 110, 280 98 S 100 80, 0 102 Z" fill="oklch(0.8 0.07 74)" />
        </g>
        <g stroke="oklch(0.93 0.02 84)" stroke-width="1" opacity="0.35" fill="none">
          <path d="M0 212 C 160 194, 300 232, 450 212 S 580 194, 620 208" />
          <path d="M0 122 C 170 104, 320 142, 480 120 S 590 106, 620 118" />
          <path d="M0 76 C 180 58, 340 96, 500 74 S 600 66, 620 72" />
        </g>
        <g fill="oklch(0.96 0.02 84)" font-family="IBM Plex Sans, sans-serif" font-size="10" letter-spacing="2">
          <text x="18" y="178">HIGH-VALUE</text>
          <text x="18" y="126">CORE ACTIVE</text>
          <text x="18" y="78">NEW / SENSITIVE</text>
        </g>
      </svg>
      <div class="login-meta">
        <span>8 stores · 2,400 orders</span>
        <span>as-of 2026-11-12</span>
        <span>PG 16 / numpy kmeans</span>
      </div>
    </section>

    <section class="login-form-wrap">
      <div class="login-card">
        <div class="eyebrow">demo access</div>
        <h2>进入剖面工作台</h2>
        <p class="muted" style="margin-top: 4px">
          三个演示账号共用密码 <strong>Demo@2026</strong>，角色不同、权限不同。
        </p>

        <form class="login-form" @submit.prevent="submit">
          <div class="field">
            <label for="email">邮箱</label>
            <input
              id="email"
              v-model="email"
              class="input"
              type="email"
              autocomplete="username"
              data-testid="email-input"
              placeholder="admin@rfmseg.io"
            />
          </div>
          <div class="field">
            <label for="password">密码</label>
            <input
              id="password"
              v-model="password"
              class="input"
              type="password"
              autocomplete="current-password"
              data-testid="password-input"
              placeholder="Demo@2026"
            />
          </div>
          <button class="btn btn-primary" type="submit" :disabled="auth.loading" data-testid="login-submit">
            {{ auth.loading ? '正在校验…' : '登 录' }}
          </button>
          <ErrorNotice v-if="auth.error" :message="auth.error" :retryable="false" />
        </form>

        <div style="margin-top: 22px">
          <div class="eyebrow">快速填入</div>
          <div class="account-chips">
            <button type="button" data-testid="quick-admin" @click="fill('admin')">admin · 运营主管</button>
            <button type="button" data-testid="quick-analyst" @click="fill('analyst')">analyst · 分析师</button>
            <button type="button" data-testid="quick-viewer" @click="fill('viewer')">viewer · 店长只读</button>
          </div>
        </div>

        <div class="core-footer">
          <span>rfmseg</span>
          <span>fraunces / ibm plex</span>
          <span style="margin-left: auto">ver 1.0</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import { useAuthStore } from '../stores/authStore'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('admin@rfmseg.io')
const password = ref('Demo@2026')

function fill(role: 'admin' | 'analyst' | 'viewer') {
  email.value = `${role}@rfmseg.io`
  password.value = 'Demo@2026'
}

async function submit() {
  try {
    await auth.login(email.value, password.value)
    const redirect = (route.query.redirect as string) || '/segments'
    router.push(redirect)
  } catch {
    /* 错误信息由 auth store 呈现 */
  }
}
</script>

<style scoped>
.login-strata {
  width: 100%;
  height: auto;
  margin: 26px 0 6px;
  opacity: 0.94;
}
</style>
