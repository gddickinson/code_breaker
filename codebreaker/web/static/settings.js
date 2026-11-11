/* Settings (Round 90d): the optional Claude connection. Off by default. The key is sent once to this computer's own
   server, stored outside the project with owner-only permissions, and never shown again or sent back to the page. */
function settingsClaudeStatus(s) {
  const where = s.key_set ? `a key is set (from the ${esc(s.key_source)})` : "no key is set";
  return `<p>Status: <b>${s.enabled ? "on" : "off"}</b>; ${where}${s.sdk_installed ? "" : "; the anthropic package is not installed (pip install anthropic)"}.</p>
    <p class="mute">Model ${esc(s.model)}. Settings file: <code>${esc(s.settings_file)}</code> (outside the project, readable only by you).</p>`;
}

route(/^\/settings$/, async () => {
  const s = await api("/settings/claude");
  view().innerHTML = `<p class="kicker">// SETTINGS</p><h1>Settings</h1>
    <h2>Claude (optional)</h2><div class="panel">
      <p>Code Breaker works fully on this computer, with local models where they help. You can also let it ask Claude, Anthropic's model, as a second reader of pictures in the Lens. <b>Pictures and text sent to Claude leave this computer</b> and are processed by Anthropic, and each call is billed to the account the key belongs to. Nothing is sent unless you turn this on here <i>and</i> choose Claude for a picture.</p>
      <div id="stStatus">${settingsClaudeStatus(s)}</div>
      <h3>Add a key</h3>
      <p class="mute">Safest: set the environment variable <code>ANTHROPIC_API_KEY</code> before starting the app, and leave the box below empty. Or paste a key here: it goes only to this computer's own server, is saved to the settings file above with owner-only permissions, and is never shown again. Create and revoke keys at console.anthropic.com.</p>
      <label for="stKey">API key</label><input id="stKey" type="password" autocomplete="off" spellcheck="false" placeholder="sk-ant-...">
      <label style="display:flex;gap:8px;align-items:flex-start;margin-top:10px"><input type="checkbox" id="stAck" style="width:auto;margin-top:3px"> I understand that pictures and text I send to Claude leave this computer and that calls are billed to this key's account.</label>
      <label style="display:flex;gap:8px;align-items:flex-start"><input type="checkbox" id="stOn" style="width:auto;margin-top:3px" ${s.requested ? "checked" : ""}> Turn Claude on</label>
      <div><button id="stSave">Save</button> <button class="alt" id="stTest">Test the connection</button> <button class="alt" id="stForget">Remove the saved key and turn off</button></div>
      <p id="stMsg" aria-live="polite"></p></div>`;
  const show = r => { $("#stStatus").innerHTML = settingsClaudeStatus(r); };
  $("#stSave").onclick = ev => busy(ev.target, $("#stMsg"), async () => {
    const key = $("#stKey").value.trim();
    const r = await api("/settings/claude", { enabled: $("#stOn").checked, acknowledged: $("#stAck").checked, key: key || null });
    $("#stKey").value = "";
    show(r);
    $("#stMsg").textContent = r.enabled ? "Saved: Claude is on." : "Saved: Claude is off.";
  });
  $("#stTest").onclick = ev => busy(ev.target, $("#stMsg"), async () => {
    const r = await api("/settings/claude/test", {});
    $("#stMsg").textContent = r.message + (r.ok ? ` (${r.input_tokens} tokens in, ${r.output_tokens} out)` : "");
  });
  $("#stForget").onclick = ev => busy(ev.target, $("#stMsg"), async () => { show(await api("/settings/claude/forget", {})); $("#stMsg").textContent = "The saved key was removed; Claude is off."; });
}, "settings");
