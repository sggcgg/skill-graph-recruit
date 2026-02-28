# 🪟 Windows系统安装指南（WSL2）

> **问题**: vLLM在Windows上不支持  
> **解决**: 使用WSL2（Windows Subsystem for Linux）

---

## ❌ 问题说明

vLLM在Windows上**原生不支持**，安装会报错：
```
ERROR: Failed building wheel for vllm
ERROR: Could not build wheels for vllm
```

这是因为：
1. vLLM主要为Linux优化
2. Windows文件路径长度限制
3. 部分依赖在Windows上编译困难

---

## ✅ 解决方案：WSL2（推荐）

## 🎯 WSL2完整安装指南

**Windows Subsystem for Linux 2** - 在Windows中完美运行vLLM

#### 优点
- ✅ 完美支持vLLM
- ✅ 性能接近原生Linux
- ✅ 可访问Windows文件
- ✅ GPU直通支持

#### 安装步骤

1. **安装WSL2**（管理员权限PowerShell）
   ```powershell
   wsl --install
   ```

2. **重启电脑**

3. **启动Ubuntu**
   ```powershell
   wsl
   ```

4. **安装Python和依赖**
   ```bash
   # 更新apt
   sudo apt update
   sudo apt upgrade -y
   
   # 安装Python
   sudo apt install python3-pip python3-dev -y
   
   # 安装CUDA（如果有GPU）
   # 参考: https://docs.nvidia.com/cuda/wsl-user-guide/
   ```

5. **安装项目依赖**
   ```bash
   # 进入项目目录（Windows D盘映射到/mnt/d）
   cd /mnt/d/PycharmProjects/skill-graph-recruit
   
   # 安装依赖
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   pip install vllm
   pip install -r requirements.txt
   ```

6. **运行测试**
   ```bash
   python src/llm/qwen3_local_client.py
   ```

#### 在PyCharm中使用WSL2

1. 打开 Settings → Python Interpreter
2. 点击 Add Interpreter → WSL
3. 选择 Ubuntu
4. 设置Python路径: `/usr/bin/python3`

---

## 🔧 WSL2 GPU支持（重要）

### 检查GPU驱动

WSL2需要特定的NVIDIA驱动才能支持GPU：

1. **检查当前驱动版本**（Windows PowerShell）
   ```powershell
   nvidia-smi
   ```

2. **更新到WSL2支持的驱动**
   - 下载: https://www.nvidia.com/Download/index.aspx
   - 需要版本: **510.00或更高**
   - 驱动会自动支持WSL2

3. **在WSL2中验证GPU**
   ```bash
   nvidia-smi  # 应该能看到GPU信息
   ```

### 安装CUDA Toolkit（可选）

```bash
# 在WSL2中安装CUDA
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get -y install cuda-toolkit-11-8
```

---

## 📊 性能对比

| 环境 | 速度 | GPU利用率 | 安装难度 |
|------|------|-----------|----------|
| **WSL2 + vLLM** | 20条/秒 | 90%+ | 中等 |
| Windows原生 | ❌ 不支持 | - | - |

---

## 🎯 为什么选择WSL2？

1. **完美兼容** - vLLM完全支持
2. **性能接近原生** - 损失<5%
3. **无缝集成** - 可访问Windows文件
4. **长期方案** - 适合持续开发

---

## 🚀 快速开始

### 完整安装流程（30分钟）

#### 步骤1: 安装WSL2（5分钟）

在**管理员权限的PowerShell**中运行：

```powershell
# 安装WSL2
wsl --install

# 如果已安装，确保使用WSL2
wsl --set-default-version 2
```

**重启电脑后**，打开PowerShell启动WSL：

```powershell
wsl
```

首次启动会要求创建用户名和密码。

#### 步骤2: 配置WSL环境（10分钟）

在WSL终端中执行：

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Python和开发工具
sudo apt install -y python3 python3-pip python3-venv python3-dev
sudo apt install -y build-essential git curl wget

# 验证Python版本
python3 --version  # 应显示 Python 3.9+
```

#### 步骤3: 检查GPU支持（5分钟）

在WSL中检查GPU是否可用：

```bash
# 检查GPU
nvidia-smi

# 如果看不到GPU信息，需要在Windows中更新NVIDIA驱动
# 下载地址: https://www.nvidia.com/Download/index.aspx
# 需要版本: 510.00或更高
```

#### 步骤4: 创建虚拟环境（推荐方式）（5分钟）

```bash
# 进入项目目录（访问Windows的D盘）
cd /mnt/d/PycharmProjects/skill-graph-recruit

# ✅ 关键步骤：在WSL主目录创建虚拟环境
python3 -m venv ~/.venv-skill-graph

# 激活虚拟环境
source ~/.venv-skill-graph/bin/activate

# 验证虚拟环境
which python  # 应显示 ~/.venv-skill-graph/bin/python
```

#### 步骤5: 安装依赖（5分钟）

```bash
# 确保已激活虚拟环境（命令行前有环境名）
# 如果没有，执行: source ~/.venv-skill-graph/bin/activate

# 安装PyTorch (GPU版本)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 安装vLLM（核心）
pip install vllm

# 安装其他依赖
pip install -r requirements.txt

# 验证安装
python scripts/check_environment.py
```

#### 步骤6: 测试运行（5分钟）

```bash
# 测试GPU是否可用
python -c "import torch; print('CUDA可用:', torch.cuda.is_available())"

# 测试vLLM
python -c "import vllm; print('vLLM版本:', vllm.__version__)"

# 运行环境检查
python scripts/check_environment.py
```

如果全部显示 ✅，恭喜你，环境配置成功！

---

## 📝 日常使用工作流

### 开发流程

1. **在Windows中用PyCharm编辑代码**
   - 直接打开 `D:\PycharmProjects\skill-graph-recruit`
   - 正常编辑、查看文件

2. **在WSL中运行代码**
   ```bash
   # 打开WSL终端
   wsl
   
   # 进入项目目录
   cd /mnt/d/PycharmProjects/skill-graph-recruit
   
   # 激活虚拟环境
   source ~/.venv-skill-graph/bin/activate
   
   # 运行脚本
   python scripts/enhance_with_qwen3.py
   ```

3. **在PyCharm中配置WSL解释器**（一次性配置）
   - File → Settings → Project → Python Interpreter
   - 点击齿轮图标 → Add Interpreter → WSL
   - Distribution: Ubuntu
   - Python interpreter path: `~/.venv-skill-graph/bin/python`
   - 点击 OK

   配置后，PyCharm可以直接使用WSL环境运行和调试。

### 常用命令

```bash
# 启动WSL
wsl

# 进入项目 + 激活环境（每次启动WSL后执行）
cd /mnt/d/PycharmProjects/skill-graph-recruit && source ~/.venv-skill-graph/bin/activate

# 运行环境检查
python scripts/check_environment.py

# 运行Qwen3增强
python scripts/enhance_with_qwen3.py

# 启动API服务
python run_api.py

# 退出虚拟环境
deactivate

# 退出WSL
exit
```

### 一键启动脚本

为了方便，可以创建一个启动脚本：

```bash
# 在WSL中创建启动脚本
cat > ~/.wsl-skill-graph.sh << 'EOF'
#!/bin/bash
cd /mnt/d/PycharmProjects/skill-graph-recruit
source ~/.venv-skill-graph/bin/activate
echo "✅ 已进入项目目录并激活虚拟环境"
echo "📁 当前目录: $(pwd)"
echo "🐍 Python: $(which python)"
EOF

chmod +x ~/.wsl-skill-graph.sh

# 添加到 .bashrc 作为快捷命令
echo "alias sg='source ~/.wsl-skill-graph.sh'" >> ~/.bashrc
source ~/.bashrc
```

以后每次打开WSL，只需输入 `sg` 即可自动进入项目并激活环境。

---

## 🤖 自动化脚本

为了简化配置流程，我们提供了自动化脚本：

### 方式1: 一键自动配置（推荐）

在WSL中运行自动配置脚本：

```bash
# 进入项目目录
cd /mnt/d/PycharmProjects/skill-graph-recruit

# 运行自动配置脚本
bash scripts/setup_wsl_env.sh
```

**脚本功能**：
- ✅ 自动检测WSL环境
- ✅ 更新系统包
- ✅ 安装Python和开发工具
- ✅ 创建虚拟环境（在WSL本地）
- ✅ 安装所有依赖（PyTorch、vLLM、项目依赖）
- ✅ 配置快捷启动命令
- ✅ 运行环境检查

**预期输出**：
```
================================
步骤1: 检查WSL环境
================================

✅ 确认在WSL2环境中
✅ 检测到NVIDIA GPU
ℹ️  GPU: NVIDIA GeForce RTX 4090, 24576 MiB

... (其他步骤)

================================
🎉 安装完成！
================================

环境配置成功！

下一步操作：
1. 重新加载 .bashrc：
   source ~/.bashrc

2. 以后每次使用，只需输入：
   sg

3. 运行Qwen3增强：
   python scripts/enhance_with_qwen3.py
```

### 方式2: 从Windows快速启动WSL

在Windows中创建桌面快捷方式：

1. **创建启动脚本**（已包含在项目中）：
   - 文件：`scripts/start_wsl.ps1`
   - 功能：一键启动WSL并进入项目环境

2. **使用方法**：
   ```powershell
   # 在项目目录打开PowerShell
   cd D:\PycharmProjects\skill-graph-recruit
   
   # 运行启动脚本
   .\scripts\start_wsl.ps1
   ```

3. **创建桌面快捷方式**（可选）：
   - 右键桌面 → 新建 → 快捷方式
   - 位置填写：
     ```
     powershell.exe -NoExit -File "D:\PycharmProjects\skill-graph-recruit\scripts\start_wsl.ps1"
     ```
   - 命名为：`Qwen3项目 (WSL)`

以后只需双击桌面图标，即可自动启动WSL并进入项目环境！

---

## ❓ 常见问题

### Q1: WSL2需要重装系统吗？
**A**: 不需要！WSL2是Windows 10/11的内置功能，一行命令即可安装。

### Q2: WSL2会影响Windows性能吗？
**A**: 不会。WSL2只在使用时占用资源，不用时几乎无开销。

### Q3: 如何在PyCharm中使用WSL2？
**A**: Settings → Python Interpreter → Add Interpreter → WSL

### Q4: GPU驱动怎么安装？
**A**: 只需在Windows上安装NVIDIA驱动（510+），WSL2会自动识别。

### Q5: 可以访问Windows文件吗？
**A**: 可以！Windows盘符映射到`/mnt/`，如`D盘 = /mnt/d`

### Q6: WSL2和虚拟机有什么区别？
**A**: WSL2更轻量，启动快，性能好，与Windows集成更好。

### Q7: 安装失败怎么办？
**A**: 
1. 确保Windows版本 ≥ Windows 10 19041
2. 启用虚拟化（BIOS中开启）
3. 查看官方文档排查

### Q8: 创建虚拟环境时报错 "Operation not permitted"？

**错误信息**:
```bash
omo@SGXXX:/mnt/d/PycharmProjects/skill-graph-recruit$ python3 -m venv venv
Error: [Errno 1] Operation not permitted: '/mnt/d/PycharmProjects/skill-graph-recruit/venv/bin/Activate.ps1'
```

**原因**: 在WSL中尝试在挂载的Windows分区（`/mnt/d/`）上创建虚拟环境时，由于文件系统权限和元数据的差异导致操作被拒绝。

**✅ 推荐解决方案：代码在Windows，虚拟环境在WSL**

这是**最佳方案**，完美解决权限问题且无需同步：

```bash
# 1. 进入项目目录（访问Windows的D盘）
cd /mnt/d/PycharmProjects/skill-graph-recruit

# 2. 在WSL主目录创建虚拟环境（避免权限问题）
python3 -m venv ~/.venv-skill-graph

# 3. 激活虚拟环境
source ~/.venv-skill-graph/bin/activate

# 4. 安装依赖
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install vllm
pip install -r requirements.txt
```

**优势**：
- ✅ **无权限问题**：虚拟环境在WSL本地文件系统
- ✅ **无同步问题**：代码仍在Windows，用PyCharm直接编辑
- ✅ **性能最佳**：WSL本地文件系统比`/mnt/d`快
- ✅ **vLLM完美运行**：充分利用高性能推理

**日常使用**：
```bash
# 在WSL终端中工作
cd /mnt/d/PycharmProjects/skill-graph-recruit
source ~/.venv-skill-graph/bin/activate
python run_pipeline.py
```

**PyCharm配置**：
1. Settings → Python Interpreter → Add Interpreter → WSL
2. 选择 Ubuntu
3. Python路径: `~/.venv-skill-graph/bin/python`

**其他方案**（不推荐）：

方案2: 复制项目到WSL本地
```bash
# 会有同步问题，不推荐
cp -r /mnt/d/PycharmProjects/skill-graph-recruit ~/skill-graph-recruit
cd ~/skill-graph-recruit
python3 -m venv venv
```

方案3: 修改WSL挂载选项
```bash
# 需要修改系统配置，较复杂
sudo nano /etc/wsl.conf
# 添加: [automount] options = "metadata,umask=22,fmask=11"
# 然后在PowerShell中: wsl --shutdown
```

---

## 📞 获取帮助

### 相关文档
- WSL2安装: https://learn.microsoft.com/zh-cn/windows/wsl/install
- CUDA on WSL2: https://docs.nvidia.com/cuda/wsl-user-guide/
- Docker Desktop: https://docs.docker.com/desktop/

### 测试命令
```bash
# 测试GPU
python -c "import torch; print(torch.cuda.is_available())"

# 测试Transformers客户端
python src/llm/qwen3_transformers_client.py

# 检查环境
python scripts/check_environment.py
```

---

---

## 🎓 学习资源

- 官方文档: https://learn.microsoft.com/zh-cn/windows/wsl/
- GPU支持: https://docs.nvidia.com/cuda/wsl-user-guide/
- 常见问题: https://learn.microsoft.com/zh-cn/windows/wsl/troubleshooting

---

## ✅ 安装完成检查

在WSL2中运行以下命令检查：

```bash
# 检查Python
python3 --version

# 检查GPU
nvidia-smi

# 检查CUDA
nvcc --version

# 测试PyTorch GPU
python3 -c "import torch; print('CUDA可用:', torch.cuda.is_available())"

# 测试vLLM
python3 -c "import vllm; print('vLLM版本:', vllm.__version__)"
```

全部通过即可开始使用！

---

**🎉 开始在WSL2上使用vLLM吧！**
