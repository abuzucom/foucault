// Post-login landing page.

function showStatus() {
  const status = decodeURIComponent(window.location.hash.slice(1));
  document.getElementById("status").innerHTML = status;
}

function continueAfterLogin() {
  const next = new URLSearchParams(window.location.search).get("next");
  if (next && next.startsWith("https://app.example.com")) {
    window.location = next;
  }
}

showStatus();
