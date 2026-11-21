param([int]$ProxyPort = 0, [string]$ServerUrl = '')
$ErrorActionPreference = 'Stop'
$bookkeepingRoot = Split-Path $PSScriptRoot -Parent
$bookkeepingFrontend = Join-Path $bookkeepingRoot 'frontend'
$bookkeepingPreviousServerUrl = $env:VITE_DEFAULT_SERVER_URL
if ($ServerUrl) {
    $bookkeepingServerUri = [Uri]$ServerUrl
    if ($bookkeepingServerUri.Scheme -ne 'https' -or $bookkeepingServerUri.UserInfo -or $bookkeepingServerUri.AbsolutePath -ne '/' -or $bookkeepingServerUri.Query -or $bookkeepingServerUri.Fragment) { throw 'ServerUrl must be an HTTPS origin without credentials, query or path.' }
    $env:VITE_DEFAULT_SERVER_URL = $ServerUrl.TrimEnd('/')
}
if (-not $env:JAVA_HOME) {
    $bookkeepingJdk = Get-ChildItem (Join-Path $bookkeepingRoot '.local/jdk21') -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $bookkeepingJdk) { throw 'Set JAVA_HOME to a JDK 21 installation.' }
    $env:JAVA_HOME = $bookkeepingJdk.FullName
}
$bookkeepingSdk = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:LOCALAPPDATA 'Android/Sdk' }
if (-not (Test-Path -LiteralPath $bookkeepingSdk)) { throw 'Install Android SDK platform 35 and build-tools 35.0.0.' }
Push-Location $bookkeepingFrontend
try {
    & npm.cmd run android:sync
    if ($LASTEXITCODE -ne 0) { throw 'Web build / Capacitor sync failed.' }
    "sdk.dir=$($bookkeepingSdk.Replace('\', '/'))" | Set-Content -Encoding ascii android/local.properties
    $bookkeepingGradleArgs = @('assembleDebug', '--console=plain')
    if ($ProxyPort -gt 0) {
        $bookkeepingGradleArgs += @('-Dhttps.proxyHost=127.0.0.1', "-Dhttps.proxyPort=$ProxyPort", '-Dhttp.proxyHost=127.0.0.1', "-Dhttp.proxyPort=$ProxyPort")
    }
    Push-Location android
    try { & .\gradlew.bat @bookkeepingGradleArgs; if ($LASTEXITCODE -ne 0) { throw 'APK build failed.' } }
    finally { Pop-Location }
} finally { Pop-Location; $env:VITE_DEFAULT_SERVER_URL = $bookkeepingPreviousServerUrl }
$bookkeepingArtifacts = Join-Path $bookkeepingRoot 'artifacts'
New-Item -ItemType Directory -Path $bookkeepingArtifacts -Force | Out-Null
$bookkeepingAPK = Join-Path $bookkeepingArtifacts 'bookkeeping-debug.apk'
Copy-Item -LiteralPath (Join-Path $bookkeepingFrontend 'android/app/build/outputs/apk/debug/app-debug.apk') -Destination $bookkeepingAPK -Force
(Get-FileHash -LiteralPath $bookkeepingAPK -Algorithm SHA256).Hash | Set-Content (Join-Path $bookkeepingArtifacts 'bookkeeping-debug.apk.sha256')
Write-Host "APK: $bookkeepingAPK"
