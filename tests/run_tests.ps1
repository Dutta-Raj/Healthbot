# run_tests.ps1 (Fixed)
# Script to run all unit tests with different options

param(
    [Parameter(Position=0)]
    [ValidateSet("all", "unit", "integration", "auth", "database", "kafka", "api", "medical", "rag")]
    [string]$TestType = "all",
    
    [switch]$WithCoverage,
    [switch]$VerboseOutput,
    [switch]$Quick,
    [string]$SpecificTest = ""
)

Write-Host @"
╔══════════════════════════════════════════════════════════════╗
║              RUNNING CHATBOT UNIT TESTS                      ║
╚══════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

# Build pytest command
$pytestCmd = "pytest"

if ($VerboseOutput) {
    $pytestCmd += " -v"
}

if ($WithCoverage) {
    $pytestCmd += " --cov=. --cov-report=term --cov-report=html"
}

if ($Quick) {
    $pytestCmd += " -m 'not slow'"
}

# Select test files based on type
switch ($TestType) {
    "unit" { $pytestCmd += " -m unit" }
    "integration" { $pytestCmd += " -m integration" }
    "auth" { $pytestCmd += " tests/test_auth_endpoints.py" }
    "database" { $pytestCmd += " tests/test_database_modules.py" }
    "kafka" { $pytestCmd += " tests/test_kafka_modules.py" }
    "api" { $pytestCmd += " tests/test_api_endpoints.py" }
    "medical" { $pytestCmd += " tests/test_medical_filter.py" }
    "rag" { $pytestCmd += " tests/test_rag_pipeline.py" }
    "all" { $pytestCmd += " tests/" }
}

if ($SpecificTest) {
    $pytestCmd += " -k $SpecificTest"
}

Write-Host "`nRunning command: $pytestCmd" -ForegroundColor Yellow
Write-Host ""

# Run the tests
Invoke-Expression $pytestCmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ All tests passed!" -ForegroundColor Green
    
    if ($WithCoverage) {
        Write-Host "`n📊 Coverage report generated in: htmlcov/index.html" -ForegroundColor Cyan
        Write-Host "   Open in browser: start htmlcov\index.html" -ForegroundColor Gray
    }
} else {
    Write-Host "`n❌ Some tests failed. Check the output above." -ForegroundColor Red
}

Write-Host "`n" + "="*60
