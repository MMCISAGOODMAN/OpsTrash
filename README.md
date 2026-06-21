# Ops Trash / 运维回收站

[English](#english) | [中文](#中文)

---

## English

A lightweight operations "recycle bin" for Linux and macOS, implemented in pure Python (standard library only). It intercepts `rm` via shell alias, moves files to `~/.ops_trash`, and provides CLI plus Web UI for listing, restoring, and cleaning deleted files.

### Features

- **Safe delete** — `rm` alias moves files to `~/.ops_trash` instead of permanent deletion
- **CLI** — `trash-put`, `undo` commands: list, restore, clean, search, stats, web, config
- **Web UI** — Built-in HTTP server with Bootstrap 5 frontend (Chinese / English)
- **Reliable storage** — Atomic metadata writes, file locking, permission preservation
- **Zero dependencies** — Python 3.6+ standard library only

### Quick Install

```bash
./install.sh
```

Add launchers to your PATH (`~/.local/bin`) and create `~/.ops_trash` with default config.

Enable `rm` interception in `~/.bashrc` or `~/.zshrc`:

```bash
alias rm='trash-put'
alias undo='undo'
```

### CLI Usage

```bash
# Move files into trash
trash-put /var/log/nginx/access.log

# List deleted files
undo list --limit 20

# Restore the most recently deleted file
undo last

# Restore by ID
undo restore 1 2 3

# Clean files older than 7 days (default)
undo clean
undo clean 14

# Search
undo search nginx

# Stats
undo stats
undo size

# Show / update config
undo config show
undo config set max_retention_days 14
```

### Web UI

Start the web server:

```bash
undo web --port 8080
undo web --host 127.0.0.1 --port 8080
undo web --daemon          # background mode
```

Open in browser:

| URL | Description |
|-----|-------------|
| `http://localhost:8080/` | Dashboard |
| `http://localhost:8080/index.html` | Same as above |
| `/api/list` | JSON list of trashed files |
| `/api/stats` | JSON statistics |
| `/api/clean` | POST — clean expired files |
| `/api/restore` | POST — restore by IDs |

The Web UI supports **中文 / English** via the language toggle in the navbar. Language preference is saved in `localStorage`.

**Note:** Static assets are served under `/static/` (e.g. `/static/app.js`, `/static/style.css`).

### Project Structure

```
OpsTrash/
├── ops_trash/           # Python package
│   ├── cli.py           # CLI entry
│   ├── web.py           # HTTP server & API
│   ├── storage.py       # Trash storage layer
│   ├── static/          # Web frontend assets
│   └── templates/       # index.html
├── undo                 # CLI launcher
├── install.sh
├── uninstall.sh
└── README.md
```

### Configuration

Default config at `~/.ops_trash/config.json`:

| Key | Default | Description |
|-----|---------|-------------|
| `max_retention_days` | `7` | Files older than this are considered expired |
| `max_size_gb` | `10` | Max trash size (reserved) |
| `web_port` | `8080` | Default web port |
| `web_host` | `0.0.0.0` | Default web bind address |
| `auto_clean` | `true` | Auto clean on startup (reserved) |
| `log_enabled` | `true` | Write operation log |

### Uninstall

```bash
./uninstall.sh
```

Remove aliases from your shell rc file manually.

---

## 中文

面向 Linux / macOS 的轻量级运维「回收站」，纯 Python 标准库实现。通过 Shell 别名拦截 `rm`，将文件移至 `~/.ops_trash`，并提供 CLI 与 Web 界面进行查看、恢复和清理。

### 功能特性

- **安全删除** — 通过 `rm` 别名将文件移入回收站，而非永久删除
- **命令行** — `trash-put`、`undo` 支持 list / restore / clean / search / stats / web / config
- **Web 界面** — 内置 HTTP 服务 + Bootstrap 5 前端，支持中英文切换
- **可靠存储** — 原子写入元数据、文件锁、保留文件权限
- **零依赖** — 仅需 Python 3.6+ 标准库

### 快速安装

```bash
./install.sh
```

脚本会在 `~/.local/bin` 创建启动器，并在 `~/.ops_trash` 生成默认配置。

在 `~/.bashrc` 或 `~/.zshrc` 中添加别名以拦截 `rm`：

```bash
alias rm='trash-put'
alias undo='undo'
```

### 命令行用法

```bash
# 移入回收站
trash-put /var/log/nginx/access.log

# 列出已删除文件
undo list --limit 20

# 恢复最近删除的文件
undo last

# 按 ID 恢复
undo restore 1 2 3

# 清理过期文件（默认 7 天）
undo clean
undo clean 14

# 搜索
undo search nginx

# 统计
undo stats
undo size

# 查看 / 修改配置
undo config show
undo config set max_retention_days 14
```

### Web 界面

启动 Web 服务：

```bash
undo web --port 8080
undo web --host 127.0.0.1 --port 8080
undo web --daemon          # 后台运行
```

浏览器访问：

| 地址 | 说明 |
|------|------|
| `http://localhost:8080/` | 主面板 |
| `http://localhost:8080/index.html` | 同上 |
| `/api/list` | 回收站文件列表（JSON） |
| `/api/stats` | 统计信息（JSON） |
| `/api/clean` | POST — 清理过期文件 |
| `/api/restore` | POST — 按 ID 恢复 |

Web 界面导航栏提供 **中 / EN** 语言切换，偏好保存在浏览器 `localStorage` 中。

**说明：** 静态资源通过 `/static/` 路径提供（如 `/static/app.js`、`/static/style.css`）。

### 项目结构

```
OpsTrash/
├── ops_trash/           # Python 包
│   ├── cli.py           # 命令行入口
│   ├── web.py           # HTTP 服务与 API
│   ├── storage.py       # 回收站存储层
│   ├── static/          # Web 前端资源
│   └── templates/       # index.html 模板
├── undo                 # CLI 启动脚本
├── install.sh
├── uninstall.sh
└── README.md
```

### 配置说明

默认配置文件：`~/.ops_trash/config.json`

| 键 | 默认值 | 说明 |
|----|--------|------|
| `max_retention_days` | `7` | 超过此天数的文件视为过期 |
| `max_size_gb` | `10` | 回收站容量上限（预留） |
| `web_port` | `8080` | Web 默认端口 |
| `web_host` | `0.0.0.0` | Web 默认绑定地址 |
| `auto_clean` | `true` | 启动时自动清理（预留） |
| `log_enabled` | `true` | 是否记录操作日志 |

### 卸载

```bash
./uninstall.sh
```

请手动从 Shell 配置文件中移除相关别名。

---

License: MIT
