<template>
  <div id="app">
    <el-container style="min-height: 100vh">
      <!-- 顶部导航 -->
      <el-header style="background: #1a1a2e; color: #fff; display: flex; align-items: center; padding: 0 12px; height: 50px;">
        <div style="display: flex; align-items: center; gap: 4px; cursor: pointer;" @click="$router.push('/')">
          <span style="font-size: 18px; font-weight: 700; color: #16c79a;">FinSight</span>
        </div>
        <div style="flex: 1;"></div>
        <div style="display: flex; align-items: center; gap: 2px;">
          <router-link to="/" style="text-decoration:none; color:#ccc; font-size:13px; padding:6px 10px; border-radius:6px;" active-class="nav-active" exact-active-class="nav-active">首页</router-link>
          <router-link to="/factor" style="text-decoration:none; color:#ccc; font-size:13px; padding:6px 10px; border-radius:6px;" active-class="nav-active">因子选股</router-link>
          <router-link to="/predict" style="text-decoration:none; color:#ccc; font-size:13px; padding:6px 10px; border-radius:6px;" active-class="nav-active">趋势预测</router-link>
          <router-link to="/anomaly" style="text-decoration:none; color:#ccc; font-size:13px; padding:6px 10px; border-radius:6px;" active-class="nav-active">异常检测</router-link>
          <router-link to="/chat" style="text-decoration:none; color:#ffd700; font-size:13px; font-weight:700; padding:6px 10px; border-radius:6px;" active-class="nav-active">股小查</router-link>
        </div>
      </el-header>

      <!-- 主内容 -->
      <el-main style="background: #f5f6fa; padding: 20px;">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<style>
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
.nav-active { color: #16c79a !important; background: rgba(22,199,154,0.1); }
</style>
