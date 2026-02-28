<template>
  <!-- Navbar 主体：不包含任何 dialog，避免 position:fixed + backdrop-filter 堆叠上下文污染 -->
  <header class="navbar">
    <div class="navbar-container">
      <div class="navbar-logo">
        <router-link to="/">
          <h1 class="logo-text">智能招聘系统</h1>
        </router-link>
        <div class="tech-badges">
          <el-tag size="small" type="primary">Qwen3.5-Plus</el-tag>
          <el-tag size="small" type="success">RAG</el-tag>
          <el-tag size="small" type="warning">Neo4j</el-tag>
        </div>
      </div>
      
      <div class="navbar-search">
        <el-input
          v-model="searchQuery"
          placeholder="搜索岗位、技能..."
          :prefix-icon="Search"
          @keyup.enter="handleSearch"
        />
        <button class="graph-search-btn" @click="handleSearch">
          <el-icon><Connection /></el-icon>
          图谱搜索
        </button>
      </div>
      
      <nav class="navbar-menu">
        <router-link 
          v-for="item in navItems" 
          :key="item.path"
          :to="item.path"
          class="nav-item"
          active-class="nav-item--active"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>

        <!-- 用户中心：已登录跳转，未登录弹登录框 -->
        <a
          class="nav-item nav-item--user-center"
          :class="{ 'nav-item--active': $route.path === '/user-center' }"
          @click="handleUserCenterClick"
        >
          <el-icon><User /></el-icon>
          <span>用户中心</span>
          <span v-if="!isLoggedIn" class="nav-lock-badge" title="需要登录">🔒</span>
        </a>
      </nav>
      
      <div class="navbar-user">
        <template v-if="isLoggedIn">
          <el-dropdown @command="handleUserCommand">
            <span class="user-dropdown">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="user-name">{{ userName }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="center">
                  <el-icon><User /></el-icon>
                  个人中心
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <el-button @click="showLoginDialog = true" style="margin-right: 8px;">登录</el-button>
          <el-button type="primary" @click="showRegisterDialog = true">注册</el-button>
        </template>
      </div>
    </div>
  </header>

  <!-- 登录/注册弹窗：完全自定义，teleport 到 body 以脱离 navbar 堆叠上下文 -->
  <teleport to="body">
    <!-- 登录弹窗 -->
    <transition name="auth-fade">
      <div v-if="showLoginDialog" class="auth-overlay" @click.self="showLoginDialog = false" @keyup.enter="handleLogin">
        <div class="auth-modal" @keyup.enter="handleLogin">
          <!-- 背景光晕装饰 -->
          <div class="auth-glow auth-glow--blue"></div>
          <div class="auth-glow auth-glow--purple"></div>

          <!-- 关闭按钮 -->
          <button class="auth-close" @click="showLoginDialog = false">✕</button>

          <!-- 顶部 logo + 标题 -->
          <div class="auth-header">
            <div class="auth-icon">🔐</div>
            <h2 class="auth-title">欢迎回来</h2>
            <p class="auth-subtitle">登录智能招聘系统</p>
          </div>

          <!-- 表单 -->
          <div class="auth-form">
            <div class="auth-field">
              <label class="auth-label">用户名</label>
              <div class="auth-input-wrap">
                <span class="auth-input-icon">👤</span>
                <input
                  v-model="loginForm.username"
                  class="auth-input"
                  type="text"
                  placeholder="请输入用户名"
                  autocomplete="username"
                  @keyup.enter="handleLogin"
                />
              </div>
            </div>
            <div class="auth-field">
              <label class="auth-label">密码</label>
              <div class="auth-input-wrap">
                <span class="auth-input-icon">🔒</span>
                <input
                  v-model="loginForm.password"
                  class="auth-input"
                  :type="showLoginPwd ? 'text' : 'password'"
                  placeholder="请输入密码"
                  autocomplete="current-password"
                  @keyup.enter="handleLogin"
                />
                <button class="auth-eye" @click="showLoginPwd = !showLoginPwd">
                  {{ showLoginPwd ? '🙈' : '👁️' }}
                </button>
              </div>
            </div>
          </div>

          <!-- 按钮区 -->
          <button
            class="auth-submit"
            :class="{ loading: authLoading }"
            :disabled="authLoading"
            @click="handleLogin"
          >
            <span v-if="!authLoading">登 录</span>
            <span v-else class="auth-spinner"></span>
          </button>

          <p class="auth-switch">
            还没有账号？
            <a @click="switchToRegister">立即注册</a>
          </p>
        </div>
      </div>
    </transition>

    <!-- 注册弹窗 -->
    <transition name="auth-fade">
      <div v-if="showRegisterDialog" class="auth-overlay" @click.self="showRegisterDialog = false">
        <div class="auth-modal" @keyup.enter="handleRegister">
          <div class="auth-glow auth-glow--purple"></div>
          <div class="auth-glow auth-glow--teal"></div>

          <button class="auth-close" @click="showRegisterDialog = false">✕</button>

          <div class="auth-header">
            <div class="auth-icon">🚀</div>
            <h2 class="auth-title">创建账号</h2>
            <p class="auth-subtitle">加入智能招聘系统</p>
          </div>

          <div class="auth-form">
            <div class="auth-field">
              <label class="auth-label">用户名</label>
              <div class="auth-input-wrap">
                <span class="auth-input-icon">👤</span>
                <input
                  v-model="registerForm.username"
                  class="auth-input"
                  type="text"
                  placeholder="请输入用户名"
                  @keyup.enter="handleRegister"
                />
              </div>
            </div>
            <div class="auth-field">
              <label class="auth-label">邮箱</label>
              <div class="auth-input-wrap">
                <span class="auth-input-icon">📧</span>
                <input
                  v-model="registerForm.email"
                  class="auth-input"
                  type="email"
                  placeholder="请输入邮箱"
                  @keyup.enter="handleRegister"
                />
              </div>
            </div>
            <div class="auth-field">
              <label class="auth-label">密码</label>
              <div class="auth-input-wrap">
                <span class="auth-input-icon">🔒</span>
                <input
                  v-model="registerForm.password"
                  class="auth-input"
                  :type="showRegPwd ? 'text' : 'password'"
                  placeholder="请输入密码（至少6位）"
                  @keyup.enter="handleRegister"
                />
                <button class="auth-eye" @click="showRegPwd = !showRegPwd">
                  {{ showRegPwd ? '🙈' : '👁️' }}
                </button>
              </div>
            </div>
          </div>

          <button
            class="auth-submit auth-submit--register"
            :class="{ loading: authLoading }"
            :disabled="authLoading"
            @click="handleRegister"
          >
            <span v-if="!authLoading">注 册</span>
            <span v-else class="auth-spinner"></span>
          </button>

          <p class="auth-switch">
            已有账号？
            <a @click="switchToLogin">立即登录</a>
          </p>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { ElMessage } from 'element-plus';
import { 
  Search, House, UserFilled, Histogram, 
  ChatLineSquare, Setting, SwitchButton, DataAnalysis, 
  Monitor, Medal, User, Connection
} from '@element-plus/icons-vue';
import { useRouter, useRoute } from 'vue-router';
import { userApi } from '@/api/userApi';

const router = useRouter();
const $route = useRoute();
const searchQuery = ref('');
const isLoggedIn = ref(false);
const userName = ref('用户');
// 登录后跳转目标（路由守卫触发登录时设置）
const pendingRedirect = ref('');

// 认证相关
const showLoginDialog = ref(false);
const showRegisterDialog = ref(false);
const authLoading = ref(false);

const loginForm = ref({ username: '', password: '' });
const registerForm = ref({ username: '', email: '', password: '' });
const showLoginPwd = ref(false);
const showRegPwd = ref(false);

interface NavItem {
  path: string;
  label: string;
  icon: any;
}

const navItems: NavItem[] = [
  { path: '/', label: '首页', icon: House },
  { path: '/search', label: '岗位搜索', icon: Histogram },
  { path: '/graph', label: '技能图谱', icon: Medal },
  { path: '/chat', label: 'AI助手', icon: ChatLineSquare },
  { path: '/match', label: '匹配看板', icon: DataAnalysis },
  { path: '/analytics', label: '数据报表', icon: DataAnalysis },
  { path: '/monitoring', label: '监控看板', icon: Monitor },
];

const checkLoginStatus = () => {
  const token = localStorage.getItem('token');
  if (token) {
    isLoggedIn.value = true;
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
    userName.value = userInfo.username || userInfo.name || '用户';
  } else {
    isLoggedIn.value = false;
    userName.value = '用户';
  }
};

// 用户中心入口：已登录直接跳转，未登录弹登录框
const handleUserCenterClick = () => {
  if (isLoggedIn.value) {
    router.push('/user-center');
  } else {
    pendingRedirect.value = '/user-center';
    showLoginDialog.value = true;
  }
};

// 路由守卫触发登录（直接输入 /user-center URL 时）
const handleShowLoginDialog = (e: Event) => {
  const redirect = (e as CustomEvent).detail?.redirect || '';
  pendingRedirect.value = redirect;
  showLoginDialog.value = true;
};

onMounted(() => {
  checkLoginStatus();
  window.addEventListener('auth-expired', handleAuthExpired);
  window.addEventListener('login-success', checkLoginStatus);
  window.addEventListener('show-login-dialog', handleShowLoginDialog);
});

onUnmounted(() => {
  window.removeEventListener('auth-expired', handleAuthExpired);
  window.removeEventListener('login-success', checkLoginStatus);
  window.removeEventListener('show-login-dialog', handleShowLoginDialog);
});

const handleAuthExpired = () => {
  isLoggedIn.value = false;
  userName.value = '用户';
  localStorage.removeItem('token');
  localStorage.removeItem('userInfo');
  ElMessage.warning('登录已过期，请重新登录');
};

const handleLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password) {
    ElMessage.warning('请填写用户名和密码');
    return;
  }
  authLoading.value = true;
  try {
    const response = await userApi.login({
      username: loginForm.value.username,
      password: loginForm.value.password
    });
    const token = (response as any).access_token || (response as any).token;
    const user = (response as any).user || { username: loginForm.value.username };
    if (token) {
      localStorage.setItem('token', token);
      localStorage.setItem('userInfo', JSON.stringify(user));
      isLoggedIn.value = true;
      userName.value = user.username || loginForm.value.username;
      showLoginDialog.value = false;
      loginForm.value = { username: '', password: '' };
      ElMessage.success('登录成功！');
      window.dispatchEvent(new Event('login-success'));
      // 如果有待跳转页面（来自路由守卫或点击用户中心），登录后自动跳转
      if (pendingRedirect.value) {
        router.push(pendingRedirect.value);
        pendingRedirect.value = '';
      }
    } else {
      ElMessage.error('登录失败，请检查用户名和密码');
    }
  } catch (error: any) {
    console.error('登录失败:', error);
    ElMessage.error(error?.response?.data?.detail || '登录失败，请检查用户名和密码');
  } finally {
    authLoading.value = false;
  }
};

const handleRegister = async () => {
  if (!registerForm.value.username || !registerForm.value.email || !registerForm.value.password) {
    ElMessage.warning('请完整填写注册信息');
    return;
  }
  if (registerForm.value.password.length < 6) {
    ElMessage.warning('密码至少6位');
    return;
  }
  authLoading.value = true;
  try {
    await userApi.register({
      username: registerForm.value.username,
      email: registerForm.value.email,
      password: registerForm.value.password
    });
    ElMessage.success('注册成功！请登录');
    showRegisterDialog.value = false;
    registerForm.value = { username: '', email: '', password: '' };
    showLoginDialog.value = true;
  } catch (error: any) {
    console.error('注册失败:', error);
    ElMessage.error(error?.response?.data?.detail || '注册失败，用户名或邮箱可能已存在');
  } finally {
    authLoading.value = false;
  }
};

const switchToRegister = () => {
  showLoginDialog.value = false;
  showRegisterDialog.value = true;
};

const switchToLogin = () => {
  showRegisterDialog.value = false;
  showLoginDialog.value = true;
};

const handleSearch = () => {
  if (searchQuery.value.trim()) {
    router.push({ path: '/search', query: { q: searchQuery.value } });
  }
};


const handleUserCommand = (command: string) => {
  switch (command) {
    case 'center':
      router.push('/user-center');
      break;
    case 'logout':
      logout();
      break;
  }
};

const logout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('userInfo');
  isLoggedIn.value = false;
  userName.value = '用户';
  router.push('/');
  ElMessage.success('已退出登录');
};
</script>

<style scoped lang="scss">
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  backdrop-filter: $glass-backdrop;
  background: rgba($bg-primary, 0.9);
  border-bottom: 1px solid $border-color;
  padding: 0 20px;

  .navbar-container {
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 64px;
    gap: 16px;

    .navbar-logo {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-shrink: 0;

      a {
        text-decoration: none;
      }

      .logo-text {
        font-size: 18px;
        font-weight: bold;
        background: linear-gradient(135deg, $primary-color 0%, #60a5fa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        white-space: nowrap;
      }

      .tech-badges {
        display: flex;
        gap: 4px;

        :deep(.el-tag) {
          font-size: 10px;
          height: 18px;
          padding: 0 6px;
          line-height: 18px;
        }
      }
    }

    .navbar-search {
      display: flex;
      align-items: center;
      gap: 8px;
      flex: 1;
      max-width: 380px;

      :deep(.el-input) {
        flex: 1;
      }

      .graph-search-btn {
        flex-shrink: 0;
        height: 36px;
        padding: 0 16px;
        display: flex;
        align-items: center;
        gap: 5px;
        border: none;
        border-radius: 8px;
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: #fff;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        white-space: nowrap;
        transition: all 0.2s;

        &:hover {
          background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(99, 102, 241, 0.45);
        }

        &:active {
          transform: translateY(0);
        }
      }
    }

    .navbar-menu {
      display: flex;
      gap: 2px;
      flex-shrink: 0;

      .nav-item {
        display: flex;
        align-items: center;
        padding: 6px 10px;
        border-radius: 6px;
        color: $text-regular;
        text-decoration: none;
        font-size: 13px;
        transition: $transition-base;
        white-space: nowrap;

        .el-icon {
          margin-right: 4px;
          font-size: 14px;
        }

        &:hover {
          background: rgba(255, 255, 255, 0.08);
          color: $text-primary;
        }

        &.nav-item--active {
          background: rgba($primary-color, 0.15);
          color: $primary-color;
        }

        // 用户中心专属：cursor pointer（因为是 <a> 不是 router-link）
        &.nav-item--user-center {
          cursor: pointer;
          user-select: none;
          position: relative;

          .nav-lock-badge {
            font-size: 10px;
            margin-left: 2px;
            opacity: 0.7;
            vertical-align: middle;
          }
        }
      }
    }

    .navbar-user {
      flex-shrink: 0;
      display: flex;
      align-items: center;
      gap: 8px;

      :deep(.el-button) {
        border-radius: 6px;
        font-size: 13px;
      }
      
      .user-dropdown {
        display: flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
        padding: 6px 10px;
        border-radius: 8px;
        transition: $transition-base;
        
        &:hover {
          background: rgba(255, 255, 255, 0.08);
        }
        
        .user-name {
          font-size: 13px;
          color: $text-primary;
        }
      }
    }
  }
}

</style>

<!-- 自定义登录/注册弹窗样式（非 scoped，因为内容 teleport 到 body 不继承 scoped） -->
<style lang="scss">
// ── 遮罩层 ────────────────────────────────────────────────────────────
.auth-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(6px);
}

// ── 弹窗主体 ──────────────────────────────────────────────────────────
.auth-modal {
  position: relative;
  width: 420px;
  max-width: calc(100vw - 40px);
  padding: 40px 36px 32px;
  border-radius: 20px;
  background: linear-gradient(145deg, #0f1428 0%, #161d3a 60%, #0f1830 100%);
  border: 1px solid rgba(59, 130, 246, 0.25);
  box-shadow: 0 0 0 1px rgba(255,255,255,0.05),
              0 24px 60px rgba(0, 0, 0, 0.6),
              0 0 40px rgba(59, 130, 246, 0.1);
  overflow: hidden;
}

// 光晕背景
.auth-glow {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(50px);
  opacity: 0.18;

  &--blue {
    width: 240px; height: 240px;
    background: #3b82f6;
    top: -80px; right: -60px;
  }
  &--purple {
    width: 200px; height: 200px;
    background: #8b5cf6;
    bottom: -60px; left: -40px;
  }
  &--teal {
    width: 180px; height: 180px;
    background: #06b6d4;
    top: -50px; left: 50%;
  }
}

// 关闭按钮
.auth-close {
  position: absolute;
  top: 16px; right: 16px;
  width: 28px; height: 28px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 50%;
  color: #94a3b8;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  &:hover { background: rgba(255,255,255,0.12); color: #fff; }
}

// 头部区域
.auth-header {
  text-align: center;
  margin-bottom: 28px;

  .auth-icon {
    font-size: 40px;
    margin-bottom: 12px;
    line-height: 1;
  }

  .auth-title {
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
    margin: 0 0 6px;
    background: linear-gradient(135deg, #fff 0%, #93c5fd 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .auth-subtitle {
    font-size: 13px;
    color: #64748b;
    margin: 0;
  }
}

// 表单
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}

.auth-field {
  .auth-label {
    display: block;
    font-size: 12px;
    font-weight: 500;
    color: #94a3b8;
    margin-bottom: 7px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }

  .auth-input-wrap {
    position: relative;
    display: flex;
    align-items: center;

    .auth-input-icon {
      position: absolute;
      left: 13px;
      font-size: 15px;
      pointer-events: none;
      z-index: 1;
    }

    .auth-input {
      width: 100%;
      box-sizing: border-box;
      padding: 11px 40px 11px 40px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 10px;
      color: #ffffff;
      font-size: 14px;
      outline: none;
      transition: all 0.2s;
      font-family: inherit;

      &::placeholder { color: #475569; }

      &:focus {
        border-color: rgba(59, 130, 246, 0.6);
        background: rgba(59, 130, 246, 0.07);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
      }

      // 去除浏览器自动填充背景
      &:-webkit-autofill {
        -webkit-box-shadow: 0 0 0 1000px #111827 inset;
        -webkit-text-fill-color: #ffffff;
      }
    }

    .auth-eye {
      position: absolute;
      right: 12px;
      background: none;
      border: none;
      cursor: pointer;
      font-size: 14px;
      padding: 0;
      color: #64748b;
      &:hover { color: #94a3b8; }
    }
  }
}

// 提交按钮
.auth-submit {
  width: 100%;
  padding: 13px;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 3px;
  cursor: pointer;
  transition: all 0.25s;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  color: #ffffff;
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.35);

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(59, 130, 246, 0.5);
  }

  &:active:not(:disabled) { transform: translateY(0); }

  &:disabled { opacity: 0.6; cursor: not-allowed; }

  &--register {
    background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
    box-shadow: 0 4px 20px rgba(139, 92, 246, 0.35);
    &:hover:not(:disabled) {
      box-shadow: 0 8px 28px rgba(139, 92, 246, 0.5);
    }
  }

  &.loading { pointer-events: none; }
}

// loading 旋转
.auth-spinner {
  display: inline-block;
  width: 18px; height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: authSpin 0.7s linear infinite;
}

@keyframes authSpin { to { transform: rotate(360deg); } }

// 切换提示
.auth-switch {
  margin: 16px 0 0;
  text-align: center;
  font-size: 13px;
  color: #64748b;

  a {
    color: #60a5fa;
    cursor: pointer;
    margin-left: 4px;
    text-decoration: none;
    &:hover { color: #93c5fd; text-decoration: underline; }
  }
}

// 弹窗过渡动画
.auth-fade-enter-active,
.auth-fade-leave-active {
  transition: all 0.25s ease;
  .auth-modal {
    transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  }
}
.auth-fade-enter-from,
.auth-fade-leave-to {
  opacity: 0;
  .auth-modal { transform: scale(0.88) translateY(20px); }
}
</style>
