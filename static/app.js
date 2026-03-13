const metaStatus = document.getElementById("metaStatus");
const uploadStatus = document.getElementById("uploadStatus");
const aiOutput = document.getElementById("aiOutput");
const serverStatus = document.getElementById("serverStatus");

async function checkBackend() {
  try {
    const res = await fetch("/api/health");
    const data = await asJson(res);
    serverStatus.textContent = data.status === "ok"
      ? "✅ Backend connected. You can use Meta + AI features."
      : "⚠️ Backend responded unexpectedly.";
  } catch (err) {
    serverStatus.textContent = "⚠️ Backend is not reachable. If you only want to preview the UI, open /static/index.html with a simple static server. For full functionality, run FastAPI with uvicorn.";
  }
}

checkBackend();

async function asJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `Request failed (${response.status})`);
  }
  return data;
}

document.getElementById("validateMetaBtn").addEventListener("click", async () => {
  const access_token = document.getElementById("accessToken").value.trim();
  const ad_account_id = document.getElementById("adAccountId").value.trim();

  try {
    metaStatus.textContent = "Validating...";
    const res = await fetch("/api/meta/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ access_token, ad_account_id }),
    });
    const data = await asJson(res);
    metaStatus.textContent = `Connected as ${data.meta_user.name} (${data.meta_user.id}) for ${data.ad_account_id}`;
  } catch (err) {
    metaStatus.textContent = `Error: ${err.message}`;
  }
});

document.getElementById("uploadAudienceBtn").addEventListener("click", async () => {
  const access_token = document.getElementById("accessToken").value.trim();
  const ad_account_id = document.getElementById("adAccountId").value.trim();
  const audience_name = document.getElementById("audienceName").value.trim();
  const fileInput = document.getElementById("emailFile");

  if (!fileInput.files.length) {
    uploadStatus.textContent = "Please select a CSV or TXT file.";
    return;
  }

  const form = new FormData();
  form.append("access_token", access_token);
  form.append("ad_account_id", ad_account_id);
  form.append("audience_name", audience_name);
  form.append("email_file", fileInput.files[0]);

  try {
    uploadStatus.textContent = "Uploading and matching emails...";
    const res = await fetch("/api/meta/upload-audience", {
      method: "POST",
      body: form,
    });
    const data = await asJson(res);
    uploadStatus.textContent = `Audience ${data.audience_id} created. ${data.accepted_email_count} emails accepted.`;
  } catch (err) {
    uploadStatus.textContent = `Error: ${err.message}`;
  }
});

document.getElementById("generateAdBtn").addEventListener("click", async () => {
  const payload = {
    objective: document.getElementById("objective").value.trim(),
    audience_description: document.getElementById("audienceDescription").value.trim(),
    offer: document.getElementById("offer").value.trim(),
    tone: document.getElementById("tone").value.trim(),
    call_to_action: document.getElementById("cta").value.trim(),
  };

  try {
    aiOutput.textContent = "Generating ad...";
    const res = await fetch("/api/ai/generate-ad", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await asJson(res);
    aiOutput.textContent = data.ad;
  } catch (err) {
    aiOutput.textContent = `Error: ${err.message}`;
  }
});
