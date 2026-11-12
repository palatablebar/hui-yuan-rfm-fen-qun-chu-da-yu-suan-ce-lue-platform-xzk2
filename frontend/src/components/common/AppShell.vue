<template>
  <div class="shell">
    <aside class="rail" aria-label="项目导航与深度刻度">
      <div class="rail-mark">SG</div>
      <div class="rail-word">stratigraphy · rfmseg</div>
      <DepthScale :max="600" :labels="[0, 150, 300, 450, 600]" />
      <div class="rail-foot">
        <span class="dot" />
        <span>PG 16</span>
        <span>SEED 600</span>
      </div>
    </aside>

    <div class="content">
      <header class="topbar">
        <div class="brand-lockup">
          <span class="brand-title">rfmseg</span>
          <span class="brand-sub">拾光咖啡 · 会员运营台</span>
        </div>
        <nav class="nav">
          <router-link to="/segments">分群总览</router-link>
          <router-link to="/members">RFM 明细</router-link>
          <router-link to="/strategy">策略配置</router-link>
          <router-link to="/outreach">名单导出</router-link>
        </nav>
        <div class="topbar-right">
          <div class="user-chip">
            <strong>{{ auth.displayName || '未登录' }}</strong>
            <span>{{ auth.roleLabel || '—' }}</span>
          </div>
          <button class="btn btn-sm" type="button" @click="logout">退出</button>
        </div>
      </header>

      <svg class="contour" viewBox="0 0 1440 900" aria-hidden="true" preserveAspectRatio="xMidYMid slice">
        <g fill="none" stroke="var(--line-strong)" stroke-width="0.7" opacity="0.3">
          <path d="M-40 140 C 220 100, 380 190, 620 150 S 1080 80, 1500 170" />
          <path d="M-40 190 C 240 150, 400 240, 650 200 S 1100 130, 1500 220" />
          <path d="M-40 250 C 200 215, 420 300, 640 260 S 1120 190, 1500 280" />
          <path d="M-40 330 C 260 280, 430 380, 700 330 S 1140 260, 1500 350" />
          <path d="M-40 420 C 240 380, 470 470, 720 425 S 1160 350, 1500 440" />
          <path d="M-40 520 C 280 470, 500 570, 760 520 S 1180 450, 1500 540" />
          <path d="M-40 640 C 300 590, 520 690, 800 640 S 1200 570, 1500 660" />
          <path d="M-40 770 C 320 720, 560 820, 840 770 S 1220 700, 1500 790" />
        </g>
      </svg>

      <main>
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import DepthScale from './DepthScale.vue'
import { useAuthStore } from '../../stores/authStore'

const auth = useAuthStore()
const router = useRouter()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.contour {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.content > main {
  position: relative;
  z-index: 1;
}
</style>
