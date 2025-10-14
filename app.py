<!-- Wayne's Advanced Email & Phone Verifier -->
<div style="min-height:100vh;background:#0b1220;padding:42px 14px;box-sizing:border-box;">
  <div style="max-width:980px;margin:0 auto;background:#0f172a;border-radius:20px;border:1px solid #1f2937;box-shadow:0 18px 55px rgba(0,0,0,.35);overflow:hidden;font-family:Inter,system-ui,Arial;">
    <!-- Header -->
    <div style="background:linear-gradient(180deg,#244ea3 0%, #1e3a8a 100%);padding:28px 34px;color:#fff;">
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="font-size:28px">🚀</div>
        <h1 style="margin:0;font-weight:800;font-size:34px;letter-spacing:.2px;">
          Wayne's Advanced Verifier
        </h1>
      </div>
      <div style="opacity:.95;margin-top:6px;font-size:14px">
        Smart Detection • Multi-Contact • Email + Phone Verification
      </div>
    </div>

    <!-- Body -->
    <div style="padding:28px 34px;color:#e5e7eb;">
      <!-- Upload zone -->
      <div style="border:2px dashed #3b82f6;border-radius:16px;padding:24px;background:#0f172a;margin-bottom:18px;">
        <div style="margin-bottom:16px;">
          <div style="font-weight:700;font-size:18px;margin-bottom:8px">Upload Your Contact List</div>
          <div style="opacity:.8;font-size:13px;margin-bottom:12px">CSV with ANY columns - we'll auto-detect emails & phones!</div>
          <input id="client" placeholder="Client name (optional)" style="width:100%;max-width:300px;padding:10px 12px;border-radius:10px;border:1px solid #334155;background:#0b1220;color:#e5e7eb;">
        </div>

        <!-- Settings -->
        <div style="display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap;">
          <div>
            <label style="font-size:13px;color:#94a3b8;display:block;margin-bottom:4px;">Max Emails per Person</label>
            <select id="maxEmails" style="padding:8px 12px;border-radius:8px;border:1px solid #334155;background:#0b1220;color:#e5e7eb;">
              <option value="1">1 Email</option>
              <option value="2">2 Emails</option>
              <option value="3" selected>3 Emails</option>
            </select>
          </div>
          <div>
            <label style="font-size:13px;color:#94a3b8;display:block;margin-bottom:4px;">Max Phones per Person</label>
            <select id="maxPhones" style="padding:8px 12px;border-radius:8px;border:1px solid #334155;background:#0b1220;color:#e5e7eb;">
              <option value="1">1 Phone</option>
              <option value="2">2 Phones</option>
              <option value="3">3 Phones</option>
              <option value="4">4 Phones</option>
              <option value="5" selected>5 Phones</option>
            </select>
          </div>
        </div>

        <input id="csv" type="file" accept=".csv" style="display:none;">
        
        <div id="fileNameDisplay" style="font-size:13px;color:#22c55e;margin-bottom:12px;display:none;padding:8px 12px;background:#0b1220;border-radius:8px;border:1px solid #1f2937;">
          📄 <strong>Selected:</strong> <span id="selectedFileName"></span>
        </div>

        <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;">
          <label for="csv" style="display:inline-flex;align-items:center;gap:8px;background:#334155;border:1px solid #475569;color:#fff;border-radius:12px;padding:12px 16px;cursor:pointer;">
            <span>📂 Choose CSV File</span>
          </label>

          <button id="run" style="display:inline-flex;align-items:center;gap:8px;background:#22c55e;border:1px solid #16a34a;color:#052e12;border-radius:12px;padding:12px 18px;font-weight:800;cursor:pointer;">
            ▶️ Start Verification
          </button>

          <label style="margin-left:auto;"><input id="dedupe" type="checkbox"> Dedupe</label>
        </div>
      </div>

      <!-- Progress -->
      <div style="display:flex;align-items:center;gap:10px;margin:6px 0;">
        <div style="width:100%;height:14px;background:#0f172a;border:1px solid #1f2937;border-radius:999px;overflow:hidden">
          <div id="bar" style="width:0%;height:100%;background:linear-gradient(90deg,#3b82f6,#06b6d4,#22c55e);transition:width .22s;"></div>
        </div>
        <div id="pct" style="width:48px;text-align:right;color:#cbd5e1;">0%</div>
      </div>
      <div id="status" style="margin:4px 0 14px 2px;font-size:13px;color:#94a3b8;">Ready to verify contacts</div>

      <!-- Results -->
      <div id="cards" style="display:flex;gap:14px;flex-wrap:wrap;margin-top:6px;"></div>
      <pre id="out" style="margin-top:10px;background:#0f172a;color:#e5e7eb;padding:14px;border-radius:12px;white-space:pre-wrap;min-height:88px;border:1px solid #1f2937;font-size:12px;"></pre>
      <div id="links" style="margin-top:12px;display:flex;gap:12px;flex-wrap:wrap;"></div>

      <div style="margin-top:14px;font-size:12px;color:#94a3b8;">
        Powered by Railway • Advanced Multi-Contact Verifier
      </div>
    </div>
  </div>
</div>

<script>
(() => {
  const API_URL = "https://email-verifier-production-7d9d.up.railway.app/verify";

  const el = id => document.getElementById(id);
  const run = el("run"), csv = el("csv"), bar = el("bar"), pct = el("pct");
  const out = el("out"), links = el("links"), status = el("status"), cards = el("cards");
  const fileNameDisplay = el("fileNameDisplay");
  const selectedFileName = el("selectedFileName");

  csv.addEventListener('change', function() {
    if (this.files && this.files[0]) {
      selectedFileName.textContent = this.files[0].name;
      fileNameDisplay.style.display = 'block';
    }
  });

  function card(title, value, color){
    const c = document.createElement("div");
    c.style = "min-width:120px;background:#0f172a;border:1px solid #1f2937;border-radius:12px;padding:12px 14px;";
    c.innerHTML = `<div style="font-size:12px;color:#94a3b8">${title}</div>
                   <div style="font-weight:900;font-size:24px;color:${color}">${value}</div>`;
    return c;
  }

  function setProgress(p){
    p = Math.max(0, Math.min(100, Math.round(p)));
    bar.style.width = p + "%";
    pct.textContent = p + "%";
  }

  run.onclick = async () => {
    try{
      if(!csv.files[0]){ alert("Pick a CSV first."); return; }

      const q = new URLSearchParams();
      const client = el("client").value.trim();
      const maxEmails = el("maxEmails").value;
      const maxPhones = el("maxPhones").value;
      
      if (client) q.set("client", client);
      q.set("max_emails", maxEmails);
      q.set("max_phones", maxPhones);
      if (el("dedupe").checked) q.set("dedupe","1");

      const fd = new FormData();
      fd.append("file", csv.files[0]);

      status.textContent = `⚡ Verifying up to ${maxEmails} emails + ${maxPhones} phones per contact...`;
      out.textContent = "";
      links.innerHTML = "";
      cards.innerHTML = "";
      setProgress(0);

      let progress = 0;
      const progressInterval = setInterval(() => {
        progress = Math.min(95, progress + 2);
        setProgress(progress);
      }, 500);

      const res = await fetch(`${API_URL}?${q.toString()}`, { method:"POST", body:fd });
      const data = await res.json();

      clearInterval(progressInterval);
      setProgress(100);
      status.textContent = `✅ Complete!`;
      out.textContent = JSON.stringify(data, null, 2);

      const v = n => (n==null?0:n);
      cards.appendChild(card("Total Rows", v(data.total_rows), "#60a5fa"));
      cards.appendChild(card("✅ Valid Emails", v(data.valid_emails), "#22c55e"));
      cards.appendChild(card("❌ Invalid Emails", v(data.invalid_emails), "#ef4444"));
      cards.appendChild(card("✅ Valid Phones", v(data.valid_phones), "#10b981"));
      cards.appendChild(card("❌ Invalid Phones", v(data.invalid_phones), "#f59e0b"));

      function btn(href, text){
        const a = document.createElement("a");
        a.href = `https://email-verifier-production-7d9d.up.railway.app${href}`;
        a.download = "";
        a.textContent = text;
        a.style = "display:inline-flex;align-items:center;gap:8px;background:#1f2937;border:1px solid #334155;color:#e5e7eb;border-radius:10px;padding:10px 14px;text-decoration:none;font-weight:700;cursor:pointer;";
        return a;
      }
      
      if (data.download) links.appendChild(btn(data.download, "⬇️ Download Verified Contacts"));

    }catch(e){
      status.textContent = "❌ Error - see details below";
      out.textContent = String(e);
      setProgress(0);
    }
  };
})();
</script>
