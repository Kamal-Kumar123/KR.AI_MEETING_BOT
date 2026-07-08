/** Google sign-in for the Chrome extension. */

const PREFER_ACCOUNT_PICKER_KEY = "prefer_google_account_picker";
const GOOGLE_ASK_ACCOUNT_KEY = "google_ask_account";

/**
 * Web OAuth client used ONLY for the account-picker redirect flow after logout.
 * Google does not support redirect URIs on Chrome Extension OAuth clients.
 * Normal extension login always uses manifest oauth2.client_id (549582...).
 * One-time setup: add getExtensionRedirectUri() to this Web client's Authorized redirect URIs.
 */
const ACCOUNT_PICKER_WEB_CLIENT_ID =
  "352284106365-ls0ul4qjur7gcbc7ropp2kdlnmi8mfri.apps.googleusercontent.com";

export function getExtensionClientId(): string {
  const oauth2 = chrome.runtime.getManifest().oauth2 as { client_id?: string } | undefined;
  return oauth2?.client_id || "";
}

export function getExtensionRedirectUri(): string {
  return chrome.identity.getRedirectURL();
}

export async function markPreferAccountPicker(): Promise<void> {
  await chrome.storage.local.set({ [PREFER_ACCOUNT_PICKER_KEY]: true });
}

async function shouldPreferAccountPicker(): Promise<boolean> {
  const data = await chrome.storage.local.get(PREFER_ACCOUNT_PICKER_KEY);
  return data[PREFER_ACCOUNT_PICKER_KEY] === true;
}

async function clearPreferAccountPicker(): Promise<void> {
  await chrome.storage.local.remove(PREFER_ACCOUNT_PICKER_KEY);
}

async function shouldUseAccountPicker(): Promise<boolean> {
  if (await shouldPreferAccountPicker()) return true;
  const data = await chrome.storage.sync.get(GOOGLE_ASK_ACCOUNT_KEY);
  return data[GOOGLE_ASK_ACCOUNT_KEY] === true;
}

async function revokeTokenAtGoogle(token: string): Promise<void> {
  try {
    await fetch(`https://accounts.google.com/o/oauth2/revoke?token=${encodeURIComponent(token)}`);
  } catch {
    /* optional */
  }
}

export async function clearGoogleAuthCache(): Promise<void> {
  await new Promise<void>((resolve) => {
    chrome.identity.getAuthToken({ interactive: false }, (token) => {
      if (!token) {
        chrome.identity.clearAllCachedAuthTokens(() => resolve());
        return;
      }
      revokeTokenAtGoogle(token).finally(() => {
        chrome.identity.removeCachedAuthToken({ token }, () => {
          chrome.identity.clearAllCachedAuthTokens(() => resolve());
        });
      });
    });
  });
}

export async function signOutGoogle(): Promise<void> {
  await chrome.storage.local.remove(["token", "userEmail"]);
  await clearGoogleAuthCache();
  await markPreferAccountPicker();
}

/** Normal extension login — always uses manifest Chrome extension client. */
function getTokenViaChromeIdentity(): Promise<string> {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ interactive: true }, (token) => {
      if (chrome.runtime.lastError || !token) {
        reject(new Error(chrome.runtime.lastError?.message || "Google login cancelled"));
        return;
      }
      resolve(token);
    });
  });
}

/** Account picker — Web OAuth client + redirect URI (Google platform requirement). */
function getTokenViaAccountPicker(): Promise<string> {
  const redirectUri = getExtensionRedirectUri();
  const authUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  authUrl.searchParams.set("client_id", ACCOUNT_PICKER_WEB_CLIENT_ID);
  authUrl.searchParams.set("response_type", "token");
  authUrl.searchParams.set("redirect_uri", redirectUri);
  authUrl.searchParams.set("scope", "openid email profile");
  authUrl.searchParams.set("prompt", "select_account");

  return new Promise((resolve, reject) => {
    chrome.identity.launchWebAuthFlow(
      { url: authUrl.toString(), interactive: true },
      (responseUrl) => {
        if (chrome.runtime.lastError) {
          const msg = chrome.runtime.lastError.message || "Google sign-in failed";
          if (msg.includes("redirect_uri_mismatch") || msg.includes("redirect_uri")) {
            reject(
              new Error(
                "Account picker setup incomplete. In Google Cloud Console → Web OAuth client → " +
                  `Authorized redirect URIs, add: ${redirectUri}`
              )
            );
            return;
          }
          reject(new Error(msg));
          return;
        }
        if (!responseUrl) {
          reject(new Error("Google login cancelled"));
          return;
        }
        const hash = new URL(responseUrl).hash.replace(/^#/, "");
        const token = new URLSearchParams(hash).get("access_token");
        if (!token) {
          reject(new Error("No access token received from Google"));
          return;
        }
        resolve(token);
      }
    );
  });
}

/**
 * Auto login → extension client (549582...).
 * After logout / account chooser setting → Web redirect flow with account picker.
 */
export async function getGoogleAccessToken(): Promise<string> {
  const usePicker = await shouldUseAccountPicker();
  if (usePicker) {
    await clearGoogleAuthCache();
    const token = await getTokenViaAccountPicker();
    await clearPreferAccountPicker();
    return token;
  }
  return getTokenViaChromeIdentity();
}
