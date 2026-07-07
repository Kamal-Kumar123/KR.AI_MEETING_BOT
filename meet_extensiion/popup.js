let isTranscribing = false;
let transcriptText = "";

const startBtn = document.getElementById("startBtn");
const finishBtn = document.getElementById("finishBtn");
const meetingMode = document.getElementById("meetingMode");
const seriesIdInput = document.getElementById("seriesId");
const seriesLabel = document.getElementById("seriesLabel");

meetingMode.addEventListener("change", () => {
  const show = meetingMode.value === "connected";
  seriesIdInput.style.display = show ? "block" : "none";
  seriesLabel.style.display = show ? "block" : "none";
});

startBtn.addEventListener("click", startTranscription);
finishBtn.addEventListener("click", finishMeetingAndShare);

function startTranscription() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs[0];
    if (!tab?.url?.includes("zoom.us")) {
      updateStatus("Open a Zoom meeting tab first.");
      return;
    }

    chrome.tabs.sendMessage(tab.id, { action: "start" }, () => {
      if (chrome.runtime.lastError) {
        updateStatus("Refresh the Zoom tab and try again.");
        return;
      }
      isTranscribing = true;
      transcriptText = "";
      document.getElementById("transcript").innerHTML = "";
      startBtn.disabled = true;
      finishBtn.disabled = false;
      updateStatus("Recording... Speak or play meeting audio.");
    });
  });
}

async function finishMeetingAndShare() {
  if (isTranscribing) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        chrome.tabs.sendMessage(tabs[0].id, { action: "stop" });
      }
    });
    isTranscribing = false;
  }

  if (!transcriptText.trim()) {
    updateStatus("No transcript captured. Try speaking during the meeting.");
    return;
  }

  const mode = meetingMode.value;
  const seriesId = seriesIdInput.value.trim();

  if (mode === "connected" && !seriesId) {
    updateStatus("Enter a Series ID for connected meetings.");
    return;
  }

  finishBtn.disabled = true;
  updateStatus("Processing meeting & generating summary...");

  try {
    const response = await fetch(`${EXTENSION_CONFIG.BACKEND_URL}/extension/finish-meeting`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transcript: transcriptText,
        mode,
        series_id: mode === "connected" ? seriesId : null,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Processing failed");
    }

    const shareUrl = data.share_url || `${EXTENSION_CONFIG.FRONTEND_URL}/?meeting_id=${data.meeting_id}`;
    updateStatus("Done! Opening share page...");
    chrome.tabs.create({ url: shareUrl });
    startBtn.disabled = false;
    finishBtn.disabled = true;
  } catch (err) {
    console.error(err);
    updateStatus(`Failed: ${err.message}. Check config.js URLs & backend.`);
    finishBtn.disabled = false;
  }
}

chrome.runtime.onMessage.addListener((request) => {
  if (request.transcript) {
    transcriptText += request.transcript + "\n";
    const transcriptDiv = document.getElementById("transcript");
    transcriptDiv.innerHTML += `<p>${request.transcript}</p>`;
    transcriptDiv.scrollTop = transcriptDiv.scrollHeight;
  }
});

function updateStatus(text) {
  document.getElementById("status").textContent = text;
}
