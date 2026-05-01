import json

from omniplan_mcp.server import mcp


@mcp.tool()
async def list_documents() -> str:
    """List all currently open OmniPlan documents.
    Note: task tools now always operate on the current front document.
    """
    from omniplan_mcp.jxa import run_jxa
    jxa_script = """
const app = Application('OmniPlan');
const docs = app.documents();
const result = docs.map(d => {
  let path = null;
  try {
    const rawPath = d.path();
    path = rawPath ? String(rawPath) : null;
  } catch (_) {
    path = null;
  }
  return { name: d.name(), path };
});
JSON.stringify({ ok: true, data: result });
"""
    raw = await run_jxa(jxa_script)
    envelope = json.loads(raw)
    return json.dumps(envelope.get("data", []))


@mcp.tool()
async def save_document() -> str:
    """Save the front OmniPlan document to disk.

    OmniPlan does NOT autosave the front document on idle — verified
    empirically against OmniPlan 4.10.2 by editing a task via MCP and
    polling `document.modified` over a 10-second window: the flag
    stayed true throughout. Explicit save is therefore the only way to
    persist changes to disk between explicit File > Save commands in
    the UI (or quit-time prompts).

    Returns:
        JSON `{"saved": true, "name": "<doc>", "modified_after": false}`
        on success. The `modified_after` field reads back the document's
        dirty flag after the save call to confirm the save took effect.
    """
    from omniplan_mcp.jxa import run_jxa

    jxa_script = """
const app = Application('OmniPlan');
const d = app.documents()[0];
const name = d.name();
let modifiedBefore = null;
try { modifiedBefore = d.modified(); } catch (_) {}
const inner = JSON.parse(app.evaluateJavascript(`(function() {
  try { document.save(); return JSON.stringify({ok:true, data:null}); }
  catch (e) { return JSON.stringify({ok:false, error: e && e.message ? e.message : String(e)}); }
})()`));
if (!inner.ok) {
  JSON.stringify({ ok: false, error: inner.error });
} else {
  // document.save() returns synchronously but the `modified` flag
  // clears asynchronously (~500ms). Poll up to 2s so the returned
  // shape matches what the user would see if they checked themselves.
  let modifiedAfter = null;
  for (let i = 0; i < 20; i++) {
    delay(0.1);
    try { modifiedAfter = d.modified(); } catch (_) { modifiedAfter = null; }
    if (modifiedAfter === false || modifiedAfter === null) break;
  }
  JSON.stringify({
    ok: true,
    data: {
      saved: true,
      name: name,
      modified_before: modifiedBefore,
      modified_after: modifiedAfter,
    },
  });
}
"""
    raw = await run_jxa(jxa_script)
    envelope = json.loads(raw)
    if not envelope.get("ok"):
        raise RuntimeError(str(envelope.get("error", "Save failed.")))
    return json.dumps(envelope["data"])
