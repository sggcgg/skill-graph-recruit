# 🔧 Neo4j Desktop WSL2 连接配置指南

## 问题说明

在 WSL2 中访问 Windows 的 Neo4j Desktop 时，默认配置下无法连接。

**原因**：
- Neo4j Desktop 默认只监听 `127.0.0.1`（仅限 Windows 本地访问）
- WSL2 的 `127.0.0.1` 和 Windows 的 `127.0.0.1` 是不同的网络空间

---

## 解决方案（3选1）

### ✅ 方案A：使用 localhost（最简单，推荐优先尝试）

**适用条件**：Windows 11 或 Windows 10 最新版本

**步骤**：
1. 测试 localhost 是否可用：
   ```bash
   python scripts/test_neo4j_localhost.py
   ```

2. 如果成功，保持配置不变：
   ```yaml
   neo4j:
     uri: "bolt://localhost:7687"
   ```

3. 直接使用：
   ```bash
   python scripts/reimport_neo4j.py
   ```

**优点**：
- ✅ 最简单，不需要修改任何配置
- ✅ IP 不会变化
- ✅ 速度快

---

### ✅ 方案B：配置 Windows 防火墙（推荐）

**步骤1：添加防火墙规则**

在 **Windows PowerShell（管理员权限）** 中运行：

```powershell
# 允许 WSL2 访问 Neo4j 端口
New-NetFirewallRule `
    -DisplayName "Neo4j for WSL2" `
    -Direction Inbound `
    -LocalPort 7687 `
    -Protocol TCP `
    -Action Allow `
    -Profile Private,Domain

# 验证规则
Get-NetFirewallRule -DisplayName "Neo4j for WSL2"
```

**步骤2：查找 Windows 主机 IP**

在 WSL2 中运行：
```bash
python scripts/find_windows_ip.py
```

**步骤3：更新配置**

假设找到的 IP 是 `172.28.65.1`：
```bash
python scripts/update_neo4j_uri.py 172.28.65.1
```

**步骤4：测试连接**
```bash
python scripts/reimport_neo4j.py
```

**优点**：
- ✅ 安全（只开放特定端口）
- ✅ 不需要修改 Neo4j 配置
- ✅ 适用于所有 Windows 版本

**缺点**：
- ⚠️ Windows IP 可能变化（重启、网络切换）

---

### ✅ 方案C：配置 Neo4j 监听所有接口（最彻底）

**步骤1：找到 Neo4j 配置文件**

1. 打开 **Neo4j Desktop**
2. 选择您的数据库
3. 点击右上角 **"..."** → **"Settings"** 或 **"Manage"** → **"Open folder"** → **"Configuration"**

或者在文件资源管理器中找到：
```
C:\Users\<你的用户名>\.Neo4jDesktop\relate-data\dbmss\dbms-<id>\conf\neo4j.conf
```

**步骤2：编辑 neo4j.conf**

找到或添加以下配置：

```properties
# 允许从所有接口访问
dbms.default_listen_address=0.0.0.0

# Bolt 连接器配置
dbms.connector.bolt.enabled=true
dbms.connector.bolt.listen_address=0.0.0.0:7687

# HTTP 连接器配置（可选）
dbms.connector.http.enabled=true
dbms.connector.http.listen_address=0.0.0.0:7474
```

**步骤3：重启 Neo4j 数据库**

在 Neo4j Desktop 中：
1. 停止数据库（Stop）
2. 启动数据库（Start）

**步骤4：查找 Windows 主机 IP**

在 WSL2 中运行：
```bash
python scripts/find_windows_ip.py
```

应该会找到类似 `172.28.65.1` 的可用 IP。

**步骤5：更新配置**
```bash
python scripts/update_neo4j_uri.py 172.28.65.1
```

**步骤6：测试连接**
```bash
python scripts/reimport_neo4j.py
```

**优点**：
- ✅ 最彻底，Neo4j 可以从任何网络访问
- ✅ 适用于所有场景

**缺点**：
- ⚠️ 安全性较低（需要配合防火墙）
- ⚠️ 需要修改 Neo4j 配置

---

## 🎯 推荐执行顺序

### 第1优先：方案A（测试 localhost）
```bash
python scripts/test_neo4j_localhost.py
```
- 如果成功：直接用，最简单 ✅
- 如果失败：继续方案B

### 第2优先：方案B（配置防火墙）
```powershell
# Windows PowerShell（管理员）
New-NetFirewallRule -DisplayName "Neo4j for WSL2" -Direction Inbound -LocalPort 7687 -Protocol TCP -Action Allow
```
```bash
# WSL2
python scripts/find_windows_ip.py
python scripts/update_neo4j_uri.py <找到的IP>
```
- 如果成功：推荐使用 ✅
- 如果失败：继续方案C

### 第3优先：方案C（配置 Neo4j）
按照方案C的步骤配置 Neo4j 监听所有接口。

---

## 📋 常见问题

### Q1: 为什么 localhost 无法访问？
**A**: WSL2 和 Windows 是独立的网络环境，WSL2 的 `localhost` 指向自己，不是 Windows。

### Q2: Windows 主机 IP 会变吗？
**A**: 可能会变（重启、网络切换），建议优先使用方案A（localhost）。

### Q3: 配置防火墙安全吗？
**A**: 安全。规则只开放 7687 端口，且仅限内网访问（Private,Domain）。

### Q4: 如何删除防火墙规则？
```powershell
# Windows PowerShell（管理员）
Remove-NetFirewallRule -DisplayName "Neo4j for WSL2"
```

### Q5: 如何验证 Neo4j 在监听哪些接口？
在 Windows PowerShell 中：
```powershell
netstat -an | findstr 7687
```
应该看到类似：
```
TCP    0.0.0.0:7687           0.0.0.0:0              LISTENING
```

---

## 🔍 故障排查

### 1. 测试端口连通性

**在 WSL2 中测试**：
```bash
# 测试 localhost
nc -zv localhost 7687

# 测试 Windows 主机 IP（替换为实际IP）
nc -zv 172.28.65.1 7687
```

**在 Windows PowerShell 中测试**：
```powershell
Test-NetConnection -ComputerName localhost -Port 7687
```

### 2. 查看 Neo4j 日志

在 Neo4j Desktop 中：
1. 点击数据库的 **"..."**
2. 选择 **"Logs"** → **"neo4j.log"**

查找错误信息。

### 3. 验证防火墙规则

```powershell
# Windows PowerShell
Get-NetFirewallRule -DisplayName "Neo4j for WSL2" | Format-List
```

### 4. 重置 WSL2 网络

如果网络完全混乱：
```powershell
# Windows PowerShell（管理员）
wsl --shutdown
```

然后重新启动 WSL2。

---

## ✅ 成功标志

当以下命令成功运行，说明配置正确：

```bash
python scripts/reimport_neo4j.py
```

应该看到：
```
✅ 成功连接到Neo4j
```

---

**文档更新时间**：2026年2月10日  
**适用版本**：Neo4j Desktop 1.5+, WSL2 (Windows 10/11)
