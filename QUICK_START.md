# 🚀 快速开始指南（Qwen3版 - 2026年2月）

> **目标**: 30分钟快速体验Qwen3本地部署+技能抽取

---

## ⚡ 最快路径（10分钟体验）

### 前置条件

- ✅ NVIDIA GPU (12GB+ 显存)
- ✅ Python 3.9+

### 快速安装

```bash
# 1. 安装核心依赖
pip install torch vllm sentence-transformers scikit-learn lightgbm

# 2. 克隆项目
git clone <your-repo-url>
cd skill-graph-recruit

# 3. 测试Qwen3
python src/llm/qwen3_local_client.py
```

**首次运行会自动下载Qwen3模型（约13GB），需要5-10分钟**

---

## 📋 完整步骤（30分钟）

### Step 1: 环境准备（10分钟）

#### 1.1 创建虚拟环境

```bash
# 使用conda（推荐）
conda create -n skill-graph python=3.10
conda activate skill-graph

# 或使用venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

#### 1.2 安装PyTorch（GPU版本）

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### 1.3 安装vLLM

```bash
pip install vllm
```

#### 1.4 安装其他依赖

```bash
pip install -r requirements.txt
```

#### 1.5 验证环境

```bash
python scripts/check_environment.py
```

**预期输出**:
```
✅ Python版本: 3.10.x
✅ PyTorch已安装: 2.0.x
✅ CUDA可用: True
✅ GPU: NVIDIA GeForce RTX 4090 (24GB)
✅ vLLM已安装: 0.4.x
```

---

### Step 2: 测试Qwen3（10分钟）

#### 2.1 测试Qwen3本地客户端

```bash
python src/llm/qwen3_local_client.py
```

**首次运行**:
- 自动下载Qwen3-7B模型（约13GB）
- 下载路径: `~/.cache/huggingface/`
- 需要5-10分钟（取决于网速）

**预期输出**:
```
================================================================================
🚀 初始化Qwen3-7B本地模型
================================================================================
✅ GPU: NVIDIA GeForce RTX 4090
✅ 显存: 24.0 GB
✅ vLLM已安装
⏳ 加载模型: Qwen/Qwen3-7B-Instruct
✅ 模型加载完成！
================================================================================

🧪 测试Qwen3本地客户端
【测试1: 单条技能提取】
✅ 提取技能: ['Python', 'Django', 'MySQL', 'Redis', 'Docker', 'Kubernetes']
   共 6 个技能

【测试2: 批量技能提取】
✅ 批量提取完成: 10 条
   平均每条: 6.5 个技能

✅ 所有测试通过！
```

#### 2.2 测试主动学习采样

```bash
python src/ml/active_learning_sampler.py
```

**预期输出**:
```
🎯 开始智能采样
总数据量: 1,000 条
目标采样: 100 条 (10.00%)
采样策略: cluster

[1/4] 提取JD文本...
✅ 提取完成: 1000 条

[2/4] 向量化JD文本...
100%|████████████████████████| 1000/1000 [00:15<00:00, 66.67it/s]
✅ 向量化完成: shape=(1000, 768)

[3/4] K-Means聚类...
✅ 聚类完成

✅ 采样完成: 100 条
```

#### 2.3 测试混合抽取器

```bash
python -c "from src.nlp.hybrid_skill_extractor import HybridSkillExtractor; print('✅ 混合抽取器导入成功')"
```

---

### Step 3: 运行完整流程（10分钟）

#### 3.1 准备数据

确保有清洗后的数据：

```bash
ls data/cleaned/
# 应该看到: boss_北京_cleaned.json, boss_上海_cleaned.json, ...
```

如果没有数据，可以使用测试数据：

```bash
python scripts/generate_test_data.py
```

#### 3.2 运行Qwen3增强脚本

```bash
python scripts/enhance_with_qwen3.py
```

**交互式选择**:

```
🚀 Qwen3-7B + 知识蒸馏 技能增强系统
================================================================================

📊 处理方案:
  1. 完整流程（推荐） - 采样1万 + 蒸馏处理全部
  2. 完整流程（大样本） - 采样2万 + 蒸馏处理全部
  3. 仅Qwen3增强 - 采样1万，不使用蒸馏
  4. 自定义参数

请输入选项 (1-4): 3  # 选择3快速测试（不使用蒸馏）
```

**预期结果**:
- 主动学习采样: 3分钟
- Qwen3推理: 8-10分钟
- 保存增强数据

---

## 🎯 核心功能演示

### 功能1: 单条技能抽取

```python
from src.nlp.hybrid_skill_extractor import HybridSkillExtractor

# 初始化抽取器
extractor = HybridSkillExtractor(
    llm_mode="local",  # 使用本地Qwen3
    llm_model="Qwen/Qwen3-7B-Instruct"
)

# 抽取技能
job = {
    'title': 'Python后端开发工程师',
    'jd_text': '负责后端开发，熟悉Python、Django、MySQL、Redis...'
}

result = extractor.extract(job, use_llm=True)

print("规则抽取:", result['stats']['rule_count'], "个")
print("LLM抽取:", result['stats']['llm_count'], "个")
print("合并后:", result['stats']['merged_count'], "个")
print("新增:", result['stats']['new_from_llm'], "个")
```

### 功能2: 批量抽取（高性能）

```python
# 批量处理（使用vLLM批处理优化）
jobs = [...]  # 1000条岗位

enhanced_jobs = extractor.batch_extract(
    jobs,
    use_llm=True,
    batch_size=32  # 批处理大小
)

print(f"处理完成: {len(enhanced_jobs)} 条")
```

### 功能3: 主动学习+蒸馏（完整流程）

```python
from src.ml.active_learning_sampler import ActiveLearningSampler
from src.ml.knowledge_distillation import SkillDistillationModel

# 1. 智能采样
sampler = ActiveLearningSampler()
sampled, labels = sampler.intelligent_sample(all_jobs, target_count=10000)

# 2. Qwen3推理
extractor = HybridSkillExtractor(llm_mode="local")
enhanced = extractor.batch_extract(sampled, use_llm=True)

# 3. 训练蒸馏模型
distill = SkillDistillationModel()
metrics = distill.train(enhanced, teacher_skill_key='llm_skills')

print(f"蒸馏模型准确率: {metrics['sample_accuracy']*100:.1f}%")

# 4. 处理剩余数据
remaining_jobs = [...]  # 剩余数据
predicted_skills = distill.predict(remaining_jobs)
```

---

## 🚀 进阶使用

### 1. 导入Neo4j

```bash
# 启动Neo4j
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# 导入数据
python scripts/reimport_neo4j.py
```

### 2. 初始化向量数据库

```bash
python scripts/init_vector_db.py
```

### 3. 启动API服务

```bash
cd src/api
uvicorn main:app --reload
```

访问: http://localhost:8000/docs

---

## 💡 性能调优建议

### GPU显存不足

```python
# 降低显存利用率
client = Qwen3LocalClient(
    gpu_memory_utilization=0.8  # 从0.9降到0.8
)

# 减小批处理大小
extractor.batch_extract(
    jobs,
    batch_size=16  # 从32降到16
)
```

### 加速推理

```python
# 使用FP16（默认已启用）
client = Qwen3LocalClient(
    dtype="half"  # FP16，比FP32快2倍
)

# 多GPU并行
client = Qwen3LocalClient(
    tensor_parallel_size=2  # 使用2块GPU
)
```

---

## ❓ 常见问题

### Q1: GPU显存不足

**错误**: `OutOfMemoryError: CUDA out of memory`

**解决**:
```python
# 降低GPU显存利用率
gpu_memory_utilization=0.7  # 从0.9降到0.7
```

### Q2: 模型下载慢

**解决**:
```bash
# 使用HuggingFace镜像
export HF_ENDPOINT=https://hf-mirror.com
python src/llm/qwen3_local_client.py
```

### Q3: vLLM安装失败

**解决**:
```bash
# 方案1: 指定CUDA版本
pip install vllm --extra-index-url https://download.pytorch.org/whl/cu118

# 方案2: 从源码安装
pip install git+https://github.com/vllm-project/vllm.git
```

### Q4: 推理速度慢

**检查**:
1. GPU利用率（nvidia-smi）
2. 批处理大小（增加到32或64）
3. 是否使用FP16

---

## 📚 下一步

1. **阅读详细文档**: `docs/完整实施步骤-Qwen3版.md`
2. **查看性能指标**: `docs/Qwen3部署与使用指南.md`
3. **准备简历**: `docs/AI应用方向转型规划.md`

---

## 🎉 恭喜！

您已完成Qwen3本地部署和基础测试！

**下一步建议**:
- 处理完整数据集（50万+）
- 部署API服务
- 准备项目Demo

---

**需要帮助？** 查看完整文档或提交Issue！

🚀 **祝您使用愉快！**
