/** Request tab audio stream ID — must run from a user-gesture context (popup). */
export function getTabStreamId(tabId: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const tabCapture = chrome.tabCapture;
    if (!tabCapture?.getMediaStreamId) {
      reject(
        new Error(
          "Tab capture unavailable. Reload the extension in chrome://extensions and use Chrome 116+."
        )
      );
      return;
    }

    tabCapture.getMediaStreamId({ targetTabId: tabId }, (streamId) => {
      if (chrome.runtime.lastError || !streamId) {
        reject(
          new Error(
            chrome.runtime.lastError?.message ||
              "Tab capture denied — open the meeting tab and click Start Recording from there."
          )
        );
      } else {
        resolve(streamId);
      }
    });
  });
}
