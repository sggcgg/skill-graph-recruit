<script setup lang="ts">
import Navbar from '@/components/Navbar.vue';
import Footer from '@/components/Footer.vue';
</script>

<template>
  <div class="app">
    <Navbar />
    <main class="main-content">
      <router-view v-slot="{ Component, route }">
        <keep-alive :max="8">
          <component
            :is="Component"
            v-if="route.meta.keepAlive"
            :key="route.name as string"
          />
        </keep-alive>
        <component
          :is="Component"
          v-if="!route.meta.keepAlive"
          :key="route.path"
        />
      </router-view>
    </main>
    <Footer />
  </div>
</template>

<style scoped lang="scss">
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: $bg-primary;
  color: $text-primary;
}

.main-content {
  flex: 1;
  padding-top: 70px; // 为固定导航栏留出空间
  padding-bottom: 60px; // 为页脚留出空间
}
</style>
