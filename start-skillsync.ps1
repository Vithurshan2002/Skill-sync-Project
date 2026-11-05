# Start the isolated SkillSync stack; Ctrl+C stops all three owned services.
param([switch]$Check, [switch]$SmokeTest)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendPython = Join-Path $ProjectRoot "project\backend\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $BackendPython)) {
    throw "Backend Python environment is missing. Follow project/README.md."
}
$Runner = Join-Path $ProjectRoot "scripts\run_integration.py"
$RunnerArguments = @($Runner)
if ($Check) { $RunnerArguments += "--check" }
if ($SmokeTest) { $RunnerArguments += "--smoke-test" }
& $BackendPython @RunnerArguments
exit $LASTEXITCODE
