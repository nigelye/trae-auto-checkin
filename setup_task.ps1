# TRAE 每日签到 - Windows任务计划程序设置脚本
# 以管理员身份运行此脚本

$ErrorActionPreference = "Stop"

# 任务名称
$taskName = "TRAE每日签到"

# 脚本路径
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$vbsPath = Join-Path $scriptPath "run_checkin_hidden.vbs"

# 检查VBS文件是否存在
if (-not (Test-Path $vbsPath)) {
    Write-Host "错误: 找不到 $vbsPath" -ForegroundColor Red
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TRAE 每日签到 - 任务计划设置" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否已有同名任务
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "发现已存在的任务: $taskName" -ForegroundColor Yellow
    $confirm = Read-Host "是否删除并重新创建? (y/n)"
    if ($confirm -eq 'y' -or $confirm -eq 'Y') {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "已删除旧任务" -ForegroundColor Green
    } else {
        Write-Host "已取消"
        exit 0
    }
}

# 创建任务操作
$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$vbsPath`""

# 创建触发器 - 每天早上9:00
$trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM

# 创建任务设置
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5)

# 创建任务主体 - 使用当前用户
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

# 注册任务
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "每天早上9:00自动签到领取TRAE积分" `
    -Force

Write-Host ""
Write-Host "任务创建成功！" -ForegroundColor Green
Write-Host ""
Write-Host "任务名称: $taskName"
Write-Host "执行时间: 每天 09:00"
Write-Host "执行程序: $vbsPath"
Write-Host ""
Write-Host "注意事项:" -ForegroundColor Yellow
Write-Host "1. 请先配置好 checkin_config.json 中的 access_token"
Write-Host "2. 任务只会在用户登录时运行"
Write-Host "3. 如果电脑在9点处于关机状态，开机后会自动补签"
Write-Host ""

# 询问是否立即运行一次测试
$runNow = Read-Host "是否立即运行一次测试? (y/n)"
if ($runNow -eq 'y' -or $runNow -eq 'Y') {
    Write-Host "正在启动签到任务..."
    Start-ScheduledTask -TaskName $taskName
    Write-Host "任务已启动，日志文件: $(Join-Path $scriptPath 'checkin.log')"
}

Write-Host ""
Write-Host "按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
