# Git 工作流脚本

这几个脚本用于自动化本仓库的轻量开发工作流。

## 命令

### 1. 创建 WIP 检查点

会先运行仓库要求的两个回归测试，然后暂存全部改动并创建一次提交。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git-checkpoint.ps1 "WIP: admin dashboard gating"
```

如果你只是想先存一个本地检查点，不做测试，可以显式跳过：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git-checkpoint.ps1 "WIP: partial refactor" -SkipTests
```

### 2. 暂存当前开发现场

会把已跟踪和未跟踪文件一起 `stash`，方便你临时切任务。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git-park.ps1 "切去修登录页"
```

### 3. 恢复之前暂存的现场

默认恢复最近一次 `stash`：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git-resume.ps1
```

如果只想查看当前有哪些 `stash`，不做任何修改：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git-resume.ps1 -ListOnly
```
