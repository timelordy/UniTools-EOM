const net = require('net');

function rpc(method, params = {}, timeoutMs = 180000) {
  return new Promise((resolve, reject) => {
    const s = net.createConnection({ host: '127.0.0.1', port: 8080 }, () => {
      const req = {
        jsonrpc: '2.0',
        method,
        params,
        id: String(Date.now()) + Math.random().toString(16).slice(2),
      };
      s.write(JSON.stringify(req) + '\n');
    });

    let b = '';
    const t = setTimeout(() => {
      s.destroy();
      reject(new Error('timeout ' + method));
    }, timeoutMs);

    s.on('data', (d) => {
      b += d.toString();
      try {
        const obj = JSON.parse(b);
        clearTimeout(t);
        s.end();
        if (obj.error) return reject(new Error(obj.error.message || JSON.stringify(obj.error)));
        resolve(obj.result || obj);
      } catch {
        // wait for full JSON
      }
    });

    s.on('error', (e) => {
      clearTimeout(t);
      reject(e);
    });
  });
}

async function rpcSafe(method, params = {}, timeoutMs = 180000) {
  try {
    const res = await rpc(method, params, timeoutMs);
    return { ok: true, data: res };
  } catch (e) {
    return { ok: false, error: e.message || String(e) };
  }
}

function parseResultMaybeJson(x) {
  if (x == null) return x;
  if (typeof x === 'string') {
    try {
      return JSON.parse(x);
    } catch {
      return x;
    }
  }
  if (typeof x.result === 'string') {
    try {
      return JSON.parse(x.result);
    } catch {
      return x;
    }
  }
  return x.data || x.result || x;
}

function chunk(arr, size) {
  const out = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

function inc(map, key) {
  map[key] = (map[key] || 0) + 1;
}

function top(map, n, total) {
  return Object.entries(map)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([name, count]) => ({
      name,
      count,
      pct: total > 0 ? +(count * 100 / total).toFixed(1) : 0,
    }));
}

const EXCLUDED_TEMPLATE_VIEWS = new Set([
  'TSL_ЭОМ_Ключ к обозначению номера группы',
  'TSL_Описание шаблона',
]);

(async () => {
  const report = {
    startedAt: new Date().toISOString(),
    excludedTemplateViews: [...EXCLUDED_TEMPLATE_VIEWS],
    steps: {},
    errors: [],
  };

  // 1) Baseline: check_unused_orphan_elements (before)
  const baseline = await rpcSafe('check_unused_orphan_elements', {});
  if (!baseline.ok) {
    report.errors.push({ step: 'baseline', error: baseline.error });
    console.log(JSON.stringify(report, null, 2));
    process.exit(1);
  }

  const baselineData = parseResultMaybeJson(baseline.data) || {};
  const shortBefore = (((baselineData || {}).data || {}).short_elements) || [];
  const shortBeforeIds = shortBefore
    .map((x) => x && x.element_id)
    .filter((v) => Number.isInteger(v) && v > 0);

  report.steps.baseline = {
    shortCountBefore: shortBeforeIds.length,
  };

  // 2) Build exact Pass A candidate list with inclusion/exclusion reasons.
  const scanCode = `
var idsCsv = (parameters != null && parameters.Length > 0) ? (parameters[0] as string ?? "") : "";
var parts = idsCsv.Split(new[]{','}, System.StringSplitOptions.RemoveEmptyEntries);
var ids = new System.Collections.Generic.List<int>();
for (int i = 0; i < parts.Length; i++)
{
    int v;
    if (int.TryParse(parts[i].Trim(), out v) && v > 0) ids.Add(v);
}

var rows = new System.Collections.Generic.List<object>();
for (int i = 0; i < ids.Count; i++)
{
    var id = ids[i];
    var eid = new Autodesk.Revit.DB.ElementId(id);
    var e = document.GetElement(eid);
    if (e == null)
    {
        rows.Add(new { id = id, missing = true });
        continue;
    }

    string category = null;
    bool isLines = false;
    try
    {
        category = e.Category != null ? e.Category.Name : null;
        if (e.Category != null)
        {
            isLines = e.Category.Id.IntegerValue == (int)Autodesk.Revit.DB.BuiltInCategory.OST_Lines;
        }
    }
    catch { }

    bool pinKnown = true;
    bool pinned = false;
    try { pinned = e.Pinned; } catch { pinKnown = false; }

    bool grouped = false;
    int groupId = -1;
    try
    {
        var gid = e.GroupId;
        if (gid != null && gid != Autodesk.Revit.DB.ElementId.InvalidElementId && gid.IntegerValue > 0)
        {
            grouped = true;
            groupId = gid.IntegerValue;
        }
    }
    catch { }

    string ownerViewName = null;
    int ownerViewId = -1;
    bool ownerViewIsTemplate = false;
    try
    {
        var ovid = e.OwnerViewId;
        if (ovid != null && ovid != Autodesk.Revit.DB.ElementId.InvalidElementId && ovid.IntegerValue > 0)
        {
            ownerViewId = ovid.IntegerValue;
            var v = document.GetElement(ovid) as Autodesk.Revit.DB.View;
            if (v != null)
            {
                ownerViewName = v.Name;
                ownerViewIsTemplate = v.IsTemplate;
            }
        }
    }
    catch { }

    rows.Add(new {
        id = id,
        missing = false,
        category = category,
        isLines = isLines,
        pinKnown = pinKnown,
        pinned = pinned,
        grouped = grouped,
        groupId = groupId,
        ownerViewName = ownerViewName,
        ownerViewId = ownerViewId,
        ownerViewIsTemplate = ownerViewIsTemplate
    });
}

return new { rows = rows, requested = ids.Count };
`;

  const rows = [];
  const scanFailures = [];
  for (const sub of chunk(shortBeforeIds, 250)) {
    const scan = await rpcSafe('send_code_to_revit', { code: scanCode, parameters: [sub.join(',')] }, 180000);
    if (!scan.ok) {
      scanFailures.push({ size: sub.length, error: scan.error });
      continue;
    }

    const payload = parseResultMaybeJson(scan.data);
    if (!payload || !Array.isArray(payload.rows)) {
      scanFailures.push({ size: sub.length, error: 'invalid scan payload' });
      continue;
    }
    rows.push(...payload.rows);
  }

  report.steps.scan = {
    requested: shortBeforeIds.length,
    rowsReturned: rows.length,
    failures: scanFailures,
  };

  const candidates = [];
  const skippedByReasonIds = {
    not_lines: [],
    pinned: [],
    grouped: [],
    excluded_view: [],
    other_missing: [],
    other_pin_unknown: [],
  };

  const decisionRows = [];
  const rowById = new Map();

  for (const r of rows) {
    if (!r || !Number.isInteger(r.id)) continue;
    rowById.set(r.id, r);

    let include = true;
    let reason = 'included';

    if (r.missing) {
      include = false;
      reason = 'other_missing';
    } else if (r.isLines !== true) {
      include = false;
      reason = 'not_lines';
    } else if (r.pinKnown === false) {
      include = false;
      reason = 'other_pin_unknown';
    } else if (r.pinned === true) {
      include = false;
      reason = 'pinned';
    } else if (r.grouped === true || (Number.isInteger(r.groupId) && r.groupId > 0)) {
      include = false;
      reason = 'grouped';
    } else if (r.ownerViewName && EXCLUDED_TEMPLATE_VIEWS.has(String(r.ownerViewName))) {
      include = false;
      reason = 'excluded_view';
    }

    if (include) {
      candidates.push(r.id);
    } else {
      skippedByReasonIds[reason] = skippedByReasonIds[reason] || [];
      skippedByReasonIds[reason].push(r.id);
    }

    decisionRows.push({
      id: r.id,
      include,
      reason,
      category: r.category || null,
      isLines: r.isLines === true,
      pinned: r.pinned === true,
      pinKnown: r.pinKnown !== false,
      grouped: r.grouped === true,
      groupId: Number.isInteger(r.groupId) ? r.groupId : null,
      ownerViewName: r.ownerViewName || null,
      ownerViewIsTemplate: r.ownerViewIsTemplate === true,
    });
  }

  // 3) Batch delete candidates safely and log deleted IDs.
  const deleteCode = `
var idsCsv = (parameters != null && parameters.Length > 0) ? (parameters[0] as string ?? "") : "";
var parts = idsCsv.Split(new[]{','}, System.StringSplitOptions.RemoveEmptyEntries);
var ids = new System.Collections.Generic.List<int>();
for (int i = 0; i < parts.Length; i++)
{
    int v;
    if (int.TryParse(parts[i].Trim(), out v) && v > 0) ids.Add(v);
}

var deleted = new System.Collections.Generic.List<int>();
var failed = new System.Collections.Generic.List<object>();

using (var tx = new Autodesk.Revit.DB.Transaction(document, "Pass A short lines cleanup"))
{
    tx.Start();
    for (int i = 0; i < ids.Count; i++)
    {
        var id = ids[i];
        try
        {
            var eid = new Autodesk.Revit.DB.ElementId(id);
            var e = document.GetElement(eid);
            if (e == null)
            {
                failed.Add(new { id = id, error = "missing_before_delete" });
                continue;
            }

            document.Delete(eid);

            var stillThere = document.GetElement(eid);
            if (stillThere == null) deleted.Add(id);
            else failed.Add(new { id = id, error = "still_exists_after_delete" });
        }
        catch (System.Exception ex)
        {
            failed.Add(new { id = id, error = ex.Message });
        }
    }
    tx.Commit();
}

return new { requested = ids.Count, deleted = deleted, failed = failed };
`;

  const deletedIds = [];
  const deleteFailures = [];
  const deleteBatches = [];

  for (const sub of chunk(candidates, 80)) {
    const del = await rpcSafe('send_code_to_revit', { code: deleteCode, parameters: [sub.join(',')] }, 180000);
    if (!del.ok) {
      deleteFailures.push({ batchSize: sub.length, error: del.error, ids: sub });
      continue;
    }

    const payload = parseResultMaybeJson(del.data);
    const deleted = Array.isArray(payload && payload.deleted) ? payload.deleted.filter((x) => Number.isInteger(x)) : [];
    const failed = Array.isArray(payload && payload.failed) ? payload.failed : [];

    deletedIds.push(...deleted);
    deleteBatches.push({ requested: sub.length, deleted: deleted.length, failed: failed.length, failedItems: failed });
  }

  // 4) Verify result with second check_unused_orphan_elements (after)
  const afterCheck = await rpcSafe('check_unused_orphan_elements', {});
  let shortAfterCount = null;
  if (afterCheck.ok) {
    const afterData = parseResultMaybeJson(afterCheck.data) || {};
    const shortAfter = (((afterData || {}).data || {}).short_elements) || [];
    shortAfterCount = shortAfter.length;
  } else {
    report.errors.push({ step: 'after_check', error: afterCheck.error });
  }

  // 6) Save project if available
  let saveStatus = { attempted: true, ok: false, method: null, details: null };
  const saveDirect = await rpcSafe('save_project', {});
  if (saveDirect.ok) {
    saveStatus = { attempted: true, ok: true, method: 'save_project', details: saveDirect.data };
  } else {
    const saveFallbackCode = `
try
{
    document.Save();
    return new { success = true, method = "send_code_to_revit:document.Save" };
}
catch (System.Exception ex)
{
    return new { success = false, method = "send_code_to_revit:document.Save", error = ex.Message };
}
`;
    const saveFallback = await rpcSafe('send_code_to_revit', { code: saveFallbackCode, parameters: [] }, 180000);
    if (saveFallback.ok) {
      const payload = parseResultMaybeJson(saveFallback.data);
      if (payload && payload.success === true) {
        saveStatus = { attempted: true, ok: true, method: 'send_code_to_revit:document.Save', details: payload };
      } else {
        saveStatus = { attempted: true, ok: false, method: 'send_code_to_revit:document.Save', details: payload };
      }
    } else {
      saveStatus = { attempted: true, ok: false, method: 'save_project+fallback_failed', details: { directError: saveDirect.error, fallbackError: saveFallback.error } };
    }
  }

  // Build report stats.
  const deletedSet = new Set(deletedIds);
  const deletedByView = {};
  for (const id of deletedIds) {
    const r = rowById.get(id);
    const view = (r && r.ownerViewName) ? String(r.ownerViewName) : '(без вида-владельца)';
    inc(deletedByView, view);
  }

  const skippedCounts = Object.fromEntries(
    Object.entries(skippedByReasonIds).map(([k, arr]) => [k, Array.isArray(arr) ? arr.length : 0])
  );

  report.steps.passA = {
    totalShortBefore: shortBeforeIds.length,
    candidatesCount: candidates.length,
    candidatesIds: candidates,
    decisions: decisionRows,
    skippedByReasonCounts: skippedCounts,
    skippedByReasonIds,
  };

  report.steps.deletion = {
    requestedToDelete: candidates.length,
    deletedCount: deletedIds.length,
    deletedIds,
    deletedIdsFirst50: deletedIds.slice(0, 50),
    deleteFailures,
    deleteBatches,
  };

  report.steps.after = {
    shortCountAfter: shortAfterCount,
  };

  report.steps.summary = {
    shortBefore: shortBeforeIds.length,
    shortAfter: shortAfterCount,
    removed: deletedIds.length,
    skipped: shortBeforeIds.length - candidates.length,
    skippedBreakdown: {
      pinned: skippedCounts.pinned || 0,
      grouped: skippedCounts.grouped || 0,
      excludedView: skippedCounts.excluded_view || 0,
      other: (skippedCounts.not_lines || 0) + (skippedCounts.other_missing || 0) + (skippedCounts.other_pin_unknown || 0),
      otherDetails: {
        not_lines: skippedCounts.not_lines || 0,
        missing: skippedCounts.other_missing || 0,
        pin_unknown: skippedCounts.other_pin_unknown || 0,
      },
    },
    topViewsByDeleted: top(deletedByView, 10, deletedIds.length),
  };

  report.steps.saveProject = saveStatus;
  report.finishedAt = new Date().toISOString();

  console.log(JSON.stringify(report, null, 2));
})();
