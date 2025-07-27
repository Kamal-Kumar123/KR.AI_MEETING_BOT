// let isTranscribing = false;
// let accessToken = null;
// let transcriptText = ""; // Stores the complete transcript

// document.getElementById('authBtn').addEventListener('click', authWithZoom);
// document.getElementById('startBtn').addEventListener('click', startTranscription);
// document.getElementById('stopBtn').addEventListener('click', stopTranscription);
// document.getElementById('summaryBtn').addEventListener('click', redirectToFrontend);

// // Zoom OAuth Flow
// async function authWithZoom() {
//   try {
//     const clientId = "42WyEpAiRSCm2gl1PNUy5g";
//     const redirectUri = chrome.identity.getRedirectURL("zoom_oauth");
//     const authUrl = `https://zoom.us/oauth/authorize?response_type=token&client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}`;
    
//     const responseUrl = await chrome.identity.launchWebAuthFlow({
//       url: authUrl,
//       interactive: true
//     });
    
//     const url = new URL(responseUrl);
//     accessToken = url.hash.match(/access_token=([^&]*)/)[1];
    
//     chrome.storage.local.set({ zoomToken: accessToken });
//     updateStatus("Connected to Zoom");
//     fetchMeetingInfo();
//   } catch (error) {
//     console.error("Auth failed:", error);
//     updateStatus("Authentication failed");
//   }
// }

// // Fetch current meeting details
// async function fetchMeetingInfo() {
//   try {
//     const response = await fetch("https://api.zoom.us/v2/users/me/meetings?type=live", {
//       headers: {
//         "Authorization": `Bearer ${accessToken}`
//       }
//     });
    
//     const data = await response.json();
//     document.getElementById('meetingInfo').innerHTML = `
//       <h4>Your Meetings:</h4>
//       <ul>
//         ${data.meetings.map(m => `<li>${m.topic} (${m.status})</li>`).join('')}
//       </ul>
//     `;
//   } catch (error) {
//     console.error("Failed to fetch meetings:", error);
//   }
// }

// // Start/Stop Transcription Functions
// function startTranscription() {
//   chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
//     chrome.tabs.sendMessage(tabs[0].id, {action: "start"});
//     isTranscribing = true;
//     transcriptText = ""; // Reset transcript when starting new
//     document.getElementById('transcript').innerHTML = ""; // Clear previous transcript
//     updateStatus("Transcribing...");
//   });
// }

// function stopTranscription() {
//   chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
//     chrome.tabs.sendMessage(tabs[0].id, {action: "stop"});
//     isTranscribing = false;
//     updateStatus("Stopped - ready for summary");
//   });
// }

// // Redirect to Frontend with Transcript Data
// async function redirectToFrontend() {
//   if (!transcriptText.trim()) {
//     updateStatus("No transcript to summarize");
//     return;
//   }

//   updateStatus("Sending to your website...");
  
//   try {
//     // Store transcript in Chrome storage
//     await chrome.storage.local.set({ zoomTranscript: transcriptText });
    
//     // Open your frontend URL (replace with your actual frontend URL)
//     const frontendUrl = "http://localhost:3000/?source=extension";
//     chrome.tabs.create({ url: frontendUrl });
    
//   } catch (error) {
//     console.error("Redirect failed:", error);
//     updateStatus("Failed to redirect");
//   }
// }

// // Handle incoming transcripts
// chrome.runtime.onMessage.addListener((request) => {
//   if (request.transcript) {
//     transcriptText += request.transcript + "\n"; // Accumulate full transcript
//     const transcriptDiv = document.getElementById('transcript');
//     transcriptDiv.innerHTML += `<p>${request.transcript}</p>`;
//     transcriptDiv.scrollTop = transcriptDiv.scrollHeight;
//   }
// });

// function updateStatus(text) {
//   document.getElementById('status').textContent = text;
// }

// // Check existing auth on load
// chrome.storage.local.get(['zoomToken'], (result) => {
//   if (result.zoomToken) {
//     accessToken = result.zoomToken;
//     updateStatus("Connected to Zoom");
//     fetchMeetingInfo();
//   }
// });



















let isTranscribing = false;
let accessToken = null;
let transcriptText = ""; // Stores the complete transcript

document.getElementById('authBtn').addEventListener('click', authWithZoom);
document.getElementById('startBtn').addEventListener('click', startTranscription);
document.getElementById('stopBtn').addEventListener('click', stopTranscription);
document.getElementById('summaryBtn').addEventListener('click', redirectToFrontend);

// Zoom OAuth Flow
async function authWithZoom() {
  try {
    const clientId = "42WyEpAiRSCm2gl1PNUy5g";
    const redirectUri = chrome.identity.getRedirectURL("zoom_oauth");
    const authUrl = `https://zoom.us/oauth/authorize?response_type=token&client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}`;

    const responseUrl = await chrome.identity.launchWebAuthFlow({
      url: authUrl,
      interactive: true
    });

    const url = new URL(responseUrl);
    accessToken = url.hash.match(/access_token=([^&]*)/)[1];

    chrome.storage.local.set({ zoomToken: accessToken });
    updateStatus("Connected to Zoom");
    fetchMeetingInfo();
  } catch (error) {
    console.error("Auth failed:", error);
    updateStatus("Authentication failed");
  }
}

// Fetch current meeting details
async function fetchMeetingInfo() {
  try {
    const response = await fetch("https://api.zoom.us/v2/users/me/meetings?type=live", {
      headers: {
        "Authorization": `Bearer ${accessToken}`
      }
    });

    const data = await response.json();
    document.getElementById('meetingInfo').innerHTML = `
      <h4>Your Meetings:</h4>
      <ul>
        ${data.meetings.map(m => `<li>${m.topic} (${m.status})</li>`).join('')}
      </ul>
    `;
  } catch (error) {
    console.error("Failed to fetch meetings:", error);
  }
}

// Start Transcription
function startTranscription() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    chrome.tabs.sendMessage(tabs[0].id, { action: "start" });
    isTranscribing = true;
    transcriptText = ""; // Reset transcript
    document.getElementById('transcript').innerHTML = ""; // Clear previous transcript
    updateStatus("Transcribing...");
  });
}

// Stop Transcription and send transcript to backend
function stopTranscription() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    chrome.tabs.sendMessage(tabs[0].id, { action: "stop" });
    isTranscribing = false;
    updateStatus("Stopped - Saving transcript...");

    if (!transcriptText.trim()) {
      updateStatus("No transcript to save");
      return;
    }

    sendTranscriptToBackend(transcriptText);
  });
}

// Send transcript to FastAPI backend
async function sendTranscriptToBackend(transcript) {
  try {
    const response = await fetch("http://localhost:8000/save-transcript", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcript })
    });
    const data = await response.json();
    console.log("Saved transcript:", data);
    updateStatus("Transcript saved. Click summary to view.");
  } catch (err) {
    console.error("Failed to save transcript to backend:", err);
    updateStatus("Save failed");
  }
}

// Open frontend (localhost) to view summary
async function redirectToFrontend() {
  if (!transcriptText.trim()) {
    updateStatus("No transcript to summarize");
    return;
  }

  updateStatus("Opening summary...");

  try {
    const frontendUrl = "http://localhost:3000/?source=extension";
    chrome.tabs.create({ url: frontendUrl });
  } catch (error) {
    console.error("Redirect failed:", error);
    updateStatus("Failed to open frontend");
  }
}

// Add each new line of transcript to text and display
chrome.runtime.onMessage.addListener((request) => {
  if (request.transcript) {
    transcriptText += request.transcript + "\n";
    const transcriptDiv = document.getElementById('transcript');
    transcriptDiv.innerHTML += `<p>${request.transcript}</p>`;
    transcriptDiv.scrollTop = transcriptDiv.scrollHeight;
  }
});

// Show status
function updateStatus(text) {
  document.getElementById('status').textContent = text;
}

// Check saved token
chrome.storage.local.get(['zoomToken'], (result) => {
  if (result.zoomToken) {
    accessToken = result.zoomToken;
    updateStatus("Connected to Zoom");
    fetchMeetingInfo();
  }
});