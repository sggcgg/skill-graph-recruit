# Windows WSL2 快速指南

> 🎯 **核心要点**：代码在Windows，虚拟环境在WSL本地，完美运行vLLM

---

## 📋 快速检查清单

### 首次安装

- [ ] 安装WSL2：`wsl --install`（PowerShell管理员）
- [ ] 重启电脑
- [ ] 在Windows安装NVIDIA驱动（510.00+）
- [ ] 运行自动配置：`bash scripts/setup_wsl_env.sh`
- [ ] 验证安装：`python scripts/check_environment.py`

### 日常使用

- [ ] 启动WSL：`wsl`
- [ ] 进入项目：`cd /mnt/d/PycharmProjects/skill-graph-recruit`
- [ ] 激活环境：`source ~/.venv-skill-graph/bin/activate`
- [ ] 或使用快捷命令：`sg`

---

## 🚀 一键命令

### 首次配置（自动化）

```bash
# 在WSL中执行
cd /mnt/d/PycharmProjects/skill-graph-recruit
bash scripts/setup_wsl_env.sh
```

### 日常启动（Windows）

```powershell
# 在PowerShell中执行
cd D:\PycharmProjects\skill-graph-recruit
.\scripts\start_wsl.ps1
```

### 日常启动（WSL）

```bash
# 方式1: 使用快捷命令
sg

# 方式2: 手动激活
cd /mnt/d/PycharmProjects/skill-graph-recruit
source ~/.venv-skill-graph/bin/activate
```

---

## 📂 关键路径

| 内容 | Windows路径 | WSL路径 |
|------|------------|---------|
| **项目代码** | `D:\PycharmProjects\skill-graph-recruit` | `/mnt/d/PycharmProjects/skill-graph-recruit` |
| **虚拟环境** | `C:\Users\用户名\.venv-skill-graph` | `~/.venv-skill-graph` |
| **Python解释器** | - | `~/.venv-skill-graph/bin/python` |
| **HuggingFace模型** | `C:\Users\用户名\.cache\huggingface` | `~/.cache/huggingface` |

---

## 🔧 PyCharm配置

### 添加WSL解释器

1. **File** → **Settings** → **Project** → **Python Interpreter**
2. 点击齿轮图标 → **Add Interpreter** → **WSL**
3. **Distribution**: Ubuntu
4. **Python interpreter path**: `~/.venv-skill-graph/bin/python`
5. 点击 **OK**

### 验证配置

- PyCharm底部应显示：`WSL: ~/.venv-skill-graph/bin/python`
- 可以直接在PyCharm中运行和调试Python代码

---

## 💡 常用命令速查

### 环境管理

```bash
# 激活虚拟环境
source ~/.venv-skill-graph/bin/activate

# 退出虚拟环境
deactivate

# 检查环境
python scripts/check_environment.py

# 查看已安装包
pip list
```

### 项目运行

```bash
# Qwen3增强
python scripts/enhance_with_qwen3.py

# 导入Neo4j
python scripts/reimport_neo4j.py

# 初始化向量库
python scripts/init_vector_db.py

# 启动API
python run_api.py
```

### GPU检查

```bash
# 查看GPU
nvidia-smi

# 测试CUDA
python -c "import torch; print('CUDA:', torch.cuda.is_available())"

# 查看GPU详情
python -c "import torch; print(torch.cuda.get_device_name(0))"
```

### 系统信息

```bash
# 查看WSL版本
wsl --version

# 查看Linux发行版
cat /etc/os-release

# 查看Python版本
python --version

# 查看虚拟环境路径
which python
```

---

## ❓ 常见问题快速解决

### Q: 创建虚拟环境时报错 "Operation not permitted"

```bash
# ❌ 错误做法（在Windows挂载分区）
cd /mnt/d/PycharmProjects/skill-graph-recruit
python3 -m venv venv  # 会报错

# ✅ 正确做法（在WSL本地创建）
python3 -m venv ~/.venv-skill-graph
```

### Q: 找不到GPU

```bash
# 检查Windows驱动（在PowerShell）
nvidia-smi

# 检查WSL中的GPU（在WSL）
nvidia-smi

# 如果WSL中看不到GPU
# 解决：更新Windows NVIDIA驱动到510.00+
```

### Q: pip安装太慢

```bash
# 使用国内镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <package>

# 永久配置
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: 模型下载太慢

```bash
# 使用HuggingFace镜像
export HF_ENDPOINT=https://hf-mirror.com
python scripts/enhance_with_qwen3.py
```

### Q: 显存不足

```python
# 降低GPU显存利用率
# 编辑 config.yaml
qwen3:
  gpu_memory_utilization: 0.8  # 从0.9降到0.8
  batch_size: 16              # 从32降到16
```

---

## 📚 相关文档

- **完整安装指南**: [WINDOWS_SETUP.md](WINDOWS_SETUP.md)
- **Qwen3部署**: [docs/Qwen3部署与使用指南.md](docs/Qwen3部署与使用指南.md)
- **完整实施步骤**: [docs/完整实施步骤-Qwen3版.md](docs/完整实施步骤-Qwen3版.md)
- **项目README**: [README.md](README.md)

---

## 🎓 最佳实践总结

### ✅ 推荐做法

1. **虚拟环境位置**：WSL本地 `~/.venv-skill-graph`
2. **代码位置**：Windows `D:\PycharmProjects\skill-graph-recruit`
3. **编辑器**：PyCharm（Windows侧）+ WSL解释器
4. **运行环境**：WSL终端
5. **模型缓存**：WSL本地 `~/.cache/huggingface`

### ❌ 避免做法

1. 在`/mnt/d`创建虚拟环境（权限问题）
2. 在Windows原生环境安装vLLM（不支持）
3. 复制项目到WSL本地（同步麻烦）
4. 使用旧版NVIDIA驱动（<510.00）

### 💡 性能优化

1. **使用WSL本地文件系统**：虚拟环境、模型缓存
2. **代码放Windows**：方便编辑和版本管理
3. **充分利用GPU**：调整`gpu_memory_utilization`
4. **批处理优化**：根据显存调整`batch_size`

---

**🎉 祝您使用愉快！**

有问题请查看[完整文档](WINDOWS_SETUP.md)或提Issue。
