const PENDING_AUDIO_KEY = "pending_upload_audio";
const PAGE_MIC_KEY = "pending_page_mic";

export interface StoredAudio {
  base64: string;
  type: string;
  size: number;
}

async function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      resolve(result.split(",")[1] || "");
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

function base64ToBlob(base64: string, type: string): Blob {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new Blob([bytes], { type });
}

async function storeAudio(key: string, blob: Blob): Promise<number> {
  const payload: StoredAudio = {
    base64: await blobToBase64(blob),
    type: blob.type || "audio/webm",
    size: blob.size,
  };
  await chrome.storage.local.set({ [key]: payload });
  return blob.size;
}

async function loadStoredAudio(key: string, remove = true): Promise<Blob | null> {
  const result = await chrome.storage.local.get(key);
  const pending = result[key] as StoredAudio | undefined;
  if (!pending?.base64) return null;
  if (remove) await chrome.storage.local.remove(key);
  return base64ToBlob(pending.base64, pending.type || "audio/webm");
}

export function savePendingAudio(blob: Blob) {
  return storeAudio(PENDING_AUDIO_KEY, blob);
}

export function loadPendingAudio() {
  return loadStoredAudio(PENDING_AUDIO_KEY);
}

export function savePageMicAudio(blob: Blob) {
  return storeAudio(PAGE_MIC_KEY, blob);
}

export function loadPageMicAudio() {
  return loadStoredAudio(PAGE_MIC_KEY);
}

export { blobToBase64, base64ToBlob };
