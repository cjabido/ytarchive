// safari-extension/background.js
// Manages extension icon badge. Green dot on YouTube video pages, clear otherwise.
// YouTube is a SPA — URL changes via history.pushState do NOT fire status=complete,
// so we handle both changeInfo.url (SPA nav) and changeInfo.status=complete (hard load).

const isYouTubeVideo = (url) =>
  !!url && url.includes('youtube.com/watch') && new URL(url).searchParams.has('v');

const updateBadge = (tabId, url) => {
  if (isYouTubeVideo(url)) {
    chrome.action.setBadgeText({ text: '\u25cf', tabId });
    chrome.action.setBadgeBackgroundColor({ color: '#10b981', tabId });
  } else {
    chrome.action.setBadgeText({ text: '', tabId });
  }
};

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  const url = changeInfo.url || (changeInfo.status === 'complete' ? tab.url : null);
  if (url) updateBadge(tabId, url);
});
