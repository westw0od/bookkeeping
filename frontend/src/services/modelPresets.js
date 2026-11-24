// IDs and image capabilities transcribed from the user's SDU gateway catalog.
// These are gateway IDs, not model names for the vendors' direct APIs.
export const sduModelGroups = [
  { label: "山大 · 本地部署", models: [
    { id: "SDU-AI/DeepSeek-V4-Flash", vision: false },
  ] },
  { label: "阿里云 · DashScope", models: [
    { id: "Ali-dashscope/GLM-5.2", vision: false },
    { id: "Ali-dashscope/GLM-5.3-Flash", vision: true },
    { id: "Ali-dashscope/Kimi-K2.5", vision: true },
    { id: "Ali-dashscope/MiniMax-M2.5", vision: false },
    { id: "Ali-dashscope/MiniMax-M3.1-Flash", vision: true },
    { id: "Ali-dashscope/Qwen3.5-Flash", vision: true },
    { id: "Ali-dashscope/Qwen3.5-Plus", vision: true },
    { id: "Ali-dashscope/Qwen3.6-Flash", vision: false },
    { id: "Ali-dashscope/Qwen3.6-Plus", vision: true },
  ] },
  { label: "字节跳动 · 火山引擎", models: [
    { id: "ByteDance-volcengine/DeepSeek-V4-Flash-GA", vision: false },
    { id: "ByteDance-volcengine/DeepSeek-V4-Pro", vision: false },
    { id: "ByteDance-volcengine/DeepSeek-V4-Pro-GA", vision: false },
    { id: "ByteDance-volcengine/DeepSeek-V4.1-Flash", vision: false },
    { id: "ByteDance-volcengine/Doubao-Seed-2.0-Code", vision: true },
    { id: "ByteDance-volcengine/Doubao-Seed-2.0-lite", vision: true },
    { id: "ByteDance-volcengine/Doubao-Seed-2.0-mini", vision: true },
    { id: "ByteDance-volcengine/Doubao-Seed-2.0-pro", vision: true },
  ] },
];

export function modelPreset(id) {
  return sduModelGroups.flatMap(group => group.models).find(item => item.id === id);
}
