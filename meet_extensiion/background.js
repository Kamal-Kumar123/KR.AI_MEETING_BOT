// // Handle messages between components
// chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
//   if (request.type === "zoomPageDetected") {
//     chrome.action.setIcon({ path: "icon_active.png" });
//   }
// });

// // Clear token on logout
// chrome.runtime.onMessage.addListener((request) => {
//   if (request.type === "logout") {
//     chrome.storage.local.remove(['zoomToken']);
//   }
// });










// Handle icon update when Zoom page is detected
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "zoomPageDetected") {
    chrome.action.setIcon({ path: "icon_active.png" });
  }

  // Handle logout
  if (request.type === "logout") {
    chrome.storage.local.remove(['zoomToken']);
  }
});