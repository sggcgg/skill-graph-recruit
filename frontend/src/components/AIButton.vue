<template>
  <el-button 
    :class="['ai-button', `ai-button--${aiType}`, customClass]" 
    :type="buttonType"
    :loading="loading"
    @click="handleClick"
  >
    <el-icon v-if="icon" class="ai-button__icon">
      <component :is="icon" />
    </el-icon>
    <span v-if="$slots.default" class="ai-button__text">
      <slot />
    </span>
  </el-button>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ButtonProps } from 'element-plus';

export interface AIButtonProps {
  aiType?: 'primary' | 'analysis' | 'graph' | 'ai';
  buttonType?: ButtonProps['type'];
  icon?: string;
  loading?: boolean;
  customClass?: string;
}

const props = withDefaults(defineProps<AIButtonProps>(), {
  aiType: 'primary',
  buttonType: 'default',
  loading: false,
  customClass: ''
});

const emit = defineEmits<{
  click: [event: MouseEvent]
}>();

const handleClick = (event: MouseEvent) => {
  emit('click', event);
};
</script>

<style scoped lang="scss">
.ai-button {
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(
      90deg,
      transparent,
      rgba(255, 255, 255, 0.2),
      transparent
    );
    transition: left 0.8s;
  }

  &:hover::before {
    left: 100%;
  }

  &__icon {
    margin-right: 8px;
  }

  &--primary {
    background: linear-gradient(135deg, $primary-color 0%, #60a5fa 100%);
    border: none;
    color: white;
  }

  &--analysis {
    background: linear-gradient(135deg, $secondary-color 0%, #a78bfa 100%);
    border: none;
    color: white;
  }

  &--graph {
    background: linear-gradient(135deg, $success-color 0%, #34d399 100%);
    border: none;
    color: white;
  }

  &--ai {
    background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
    border: none;
    color: white;
    animation: pulse 2s infinite;
  }
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(236, 72, 153, 0.4);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(236, 72, 153, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(236, 72, 153, 0);
  }
}
</style>