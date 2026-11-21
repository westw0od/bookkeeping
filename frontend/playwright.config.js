const { defineConfig } = require("@playwright/test");
module.exports = defineConfig({
  testDir: "tests",
  timeout: 45000,
  workers: 1,
  use: { baseURL: process.env.WEB_TEST_URL || "http://127.0.0.1:8000",
    launchOptions: process.env.CHROMIUM_EXECUTABLE ? { executablePath: process.env.CHROMIUM_EXECUTABLE } : {},
    viewport: { width: 390, height: 844 }, trace: "retain-on-failure" },
  outputDir: "../artifacts/browser-tests",
});
