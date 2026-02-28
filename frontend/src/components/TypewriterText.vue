<template>
  <div class="typewriter-text">
    <span>{{displayText}}</span>
    <span v-if="showCursor" class="cursor">|</span>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';

interface Props {
  texts: string[];
  delay?: number; // 每个文本停留的时间（毫秒）
  speed?: number; // 打字速度（每字符毫秒）
}

const props = withDefaults(defineProps<Props>(), {
  delay: 2000,
  speed: 100
});

const displayText = ref('');
const showCursor = ref(true);
let currentIndex = 0;
let currentTextIndex = 0;
let isDeleting = false;
let timeoutId: NodeJS.Timeout | null = null;

const typeText = () => {
  const currentText = props.texts[currentTextIndex];
  
  if (isDeleting) {
    // 删除文本
    displayText.value = currentText.substring(0, currentIndex - 1);
    currentIndex--;
    
    if (currentIndex === 0) {
      isDeleting = false;
      currentTextIndex = (currentTextIndex + 1) % props.texts.length;
    }
  } else {
    // 输入文本
    displayText.value = currentText.substring(0, currentIndex + 1);
    currentIndex++;
    
    if (currentIndex === currentText.length) {
      // 文本输入完成，等待delay时间后开始删除
      isDeleting = true;
      setTimeout(typeText, props.delay);
      return;
    }
  }
  
  // 根据是否在删除来设置速度
  const speed = isDeleting ? props.speed / 3 : props.speed;
  timeoutId = setTimeout(typeText, speed);
};

onMounted(() => {
  // 开始打字
  timeoutId = setTimeout(typeText, props.speed);
  
  // 光标闪烁
  const cursorInterval = setInterval(() => {
    showCursor.value = !showCursor.value;
  }, 500);
  
  // 组件卸载时清理定时器
  onUnmounted(() => {
    if (timeoutId) clearTimeout(timeoutId);
    clearInterval(cursorInterval);
  });
});
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.typewriter-text {
  display: inline-block;
  min-height: 1.5em;
}

.cursor {
  color: $primary-color;
  margin-left: 2px;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>