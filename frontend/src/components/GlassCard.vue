<template>
  <div class="glass-card" :class="{ 'glass-card-transparent': transparent, [customClass]: customClass }">
    <slot />
  </div>
</template>

<script setup lang="ts">
interface Props {
  transparent?: boolean;
  customClass?: string;
}

withDefaults(defineProps<Props>(), {
  transparent: false,
  customClass: ''
});
</script>

<style scoped lang="scss">
.glass-card {
  padding: 20px;
  transition: $transition-base;

  &.glass-card-transparent {
    background: transparent;
    border: none;
    box-shadow: none;
  }
}
</style>