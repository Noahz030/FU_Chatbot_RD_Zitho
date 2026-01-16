"""
Vereinfachtes Arena Voting UI - direkt und einfach
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import requests

app = FastAPI()

# CORS mit konfigurierbaren Origins
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
if allowed_origins == ["*"]:
    # Development: Allow all
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Production: Restrict to specific domains
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
    )

@app.get("/", response_class=HTMLResponse)
def index():
    """Einfaches Voting UI"""
    api_base = os.getenv("ARENA_API_BASE", "http://arena-api:8001").rstrip("/")
    # Convert internal Docker DNS to localhost for browser access
    api_override = api_base.replace("http://arena-api:", "http://localhost:")
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Arena Voting</title>
    <style>
        body {
            font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 24px;
            background: #f4f4f4;
            color: #1f1f1f;
        }
        h1 { margin: 0 0 12px; font-weight: 600; }
        .comparison {
            background: white;
            padding: 20px;
            margin: 15px 0;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .answers {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin: 15px 0;
        }
        .answer {
            padding: 12px;
            background: #fafafa;
            border: 1px solid #e2e2e2;
            border-radius: 4px;
            font-size: 13px;
            line-height: 1.5;
        }
        .buttons {
            display: flex;
            gap: 10px;
            margin: 15px 0;
        }
        button {
            flex: 1;
            padding: 10px;
            border: 1px solid #d0d0d0;
            background: #fbfbfb;
            cursor: pointer;
            border-radius: 4px;
            font-weight: 600;
        }
        button:hover { background: #ededed; }
        button.active {
            background: #333;
            color: white;
            border-color: #333;
        }
        .submit {
            width: 100%;
            background: #333;
            color: white;
            border: none;
        }
        .submit:hover { background: #1f1f1f; }
        .voted { opacity: 0.6; }
        .voted p { color: #666; font-size: 12px; }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .loading {
            text-align: center;
            color: #999;
            padding: 20px;
        }
    </style>
</head>
<body>
    <h1>Arena Vergleich</h1>
    
    <div id="container">
        <div class="loading">⏳ Lade Vergleiche...</div>
    </div>

    <script>
        // API base: use environment-provided default or fallback to localhost
        const API = "__API_OVERRIDE__";
        let comparisons = [];
        let currentIndex = 0;
        let selectedVote = null;
        let assignedSubset = null;
        let totalInSubset = 0;
        let votedInSubset = 0;
        let votedSet = new Set();
        let sessionId = null;

        function ensureSessionId() {
            let sid = localStorage.getItem('arena_session_id');
            try {
                if (!sid && window.crypto && window.crypto.randomUUID) {
                    sid = window.crypto.randomUUID();
                }
            } catch(e) {}
            if (!sid) {
                sid = 'sid-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
            }
            localStorage.setItem('arena_session_id', sid);
            return sid;
        }

        // Session-Tracking via LocalStorage
        function getAssignedSubset() {
            const stored = localStorage.getItem('arena_subset');
            if (stored) {
                return parseInt(stored, 10);
            }
            return null;
        }

        function setAssignedSubset(subset) {
            localStorage.setItem('arena_subset', subset.toString());
            assignedSubset = subset;
        }

        async function assignSubsetIfNeeded() {
            assignedSubset = getAssignedSubset();
            if (assignedSubset === null) {
                try {
                    const resp = await fetch(API + '/arena/assign-subset');
                    const data = await resp.json();
                    setAssignedSubset(data.subset_id);
                    console.log('Assigned subset:', data.subset_id);
                } catch (e) {
                    console.error('Failed to assign subset:', e);
                    assignedSubset = 1; // Fallback
                }
            }
        }

        // Debug: Show we started
        document.getElementById('container').innerHTML = '<div class="loading">⏳ JavaScript läuft, starte Fetch...</div>';

        async function load() {
            const container = document.getElementById('container');
            
            // Subset zuweisen falls noch nicht geschehen
            await assignSubsetIfNeeded();
            sessionId = ensureSessionId();
            
            container.innerHTML = '<div class="loading">⏳ Fetching Subset ' + assignedSubset + ' von ' + API + '...</div>';
            
            try {
                const [cmpResp, votedResp] = await Promise.all([
                    fetch(API + '/arena/comparisons?subset=' + assignedSubset, {
                        method: 'GET',
                        headers: { 'Accept': 'application/json' }
                    }),
                    fetch(API + '/arena/voted?session_id=' + encodeURIComponent(sessionId), {
                        method: 'GET',
                        headers: { 'Accept': 'application/json' }
                    })
                ]);
                
                container.innerHTML = '<div class="loading">⏳ Responses erhalten</div>';
                
                if (!cmpResp.ok) throw new Error('HTTP ' + cmpResp.status + ' ' + cmpResp.statusText);
                if (!votedResp.ok) throw new Error('HTTP ' + votedResp.status + ' ' + votedResp.statusText);
                
                const data = await cmpResp.json();
                const votedData = await votedResp.json();
                comparisons = data.comparisons || [];
                votedSet = new Set((votedData.comparison_ids || []).map(String));
                totalInSubset = comparisons.length;
                votedInSubset = comparisons.filter(c => votedSet.has(String(c.id))).length;
                
                container.innerHTML = '<div class="loading">⏳ ' + comparisons.length + ' Vergleiche in Subset ' + assignedSubset + ' geladen...</div>';
                
                if (comparisons.length === 0) {
                    container.innerHTML = '<div class="error">⚠️ Keine Vergleiche in diesem Subset</div>';
                    return;
                }
                
                render();
            } catch (e) {
                container.innerHTML = 
                    '<div class="error">❌ Fehler beim Laden<br>' + 
                    'API: ' + API + '/arena/comparisons?subset=' + assignedSubset + '<br>' +
                    'Error: ' + e.message + '<br>' +
                    'Stack: ' + (e.stack || 'no stack') + '</div>';
            }
        }

        function render() {
            const container = document.getElementById('container');

            if (!comparisons || comparisons.length === 0) {
                container.innerHTML = '<div class="error">⚠️ Keine Vergleiche geladen</div>';
                return;
            }

            const unvoted = comparisons.filter(c => !votedSet.has(String(c.id)));

            if (unvoted.length === 0) {
                container.innerHTML = `
                    <div class="loading">
                        <h2>✅ Alle Fragen in deinem Subset beantwortet!</h2>
                        <p>Du hast ${totalInSubset} von ${totalInSubset} Fragen bewertet.</p>
                        <p>Vielen Dank für deine Teilnahme! 🎉</p>
                        <button class="submit" onclick="resetSession()" style="margin-top: 20px;">🔄 Erneut bewerten (Session zurücksetzen)</button>
                    </div>
                `;
                return;
            }

            const comp = unvoted[0];
            selectedVote = null;
            
            // Progress-Indicator
            const progress = `Frage ${votedInSubset + 1} von ${totalInSubset} (Subset ${assignedSubset})`;

            container.innerHTML = `
                <div class="comparison">
                    <p style="color: #666; font-size: 14px; margin: 0 0 12px;">${progress}</p>
                    <h2 id="question"></h2>
                    <div class="answers">
                        <div class="answer a">
                            <strong>Antwort A</strong><br>
                            <div id="ansA"></div>
                        </div>
                        <div class="answer b">
                            <strong>Antwort B</strong><br>
                            <div id="ansB"></div>
                        </div>
                    </div>
                    <div class="buttons">
                        <button onclick="selectVote('A')" id="btn-A">A ist besser</button>
                        <button onclick="selectVote('tie')" id="btn-tie">Unentschieden</button>
                        <button onclick="selectVote('B')" id="btn-B">B ist besser</button>
                        <button onclick="selectVote('both_bad')" id="btn-both_bad">Beide schlecht</button>
                    </div>
                    <button class="submit" onclick="submitVote('${comp.id}', ${comp.subset_id || 'assignedSubset'})">Vote abgeben</button>
                </div>
            `;

            // Safely inject text to avoid breaking markup
            const qEl = document.getElementById('question');
            const aEl = document.getElementById('ansA');
            const bEl = document.getElementById('ansB');

            if (qEl) qEl.textContent = comp.question || '';
            // Use shuffled answers for blind A/B testing
            if (aEl) aEl.textContent = comp.actual_answer_a || comp.answer_a || '';
            if (bEl) bEl.textContent = comp.actual_answer_b || comp.answer_b || '';
        }

        function selectVote(vote) {
            selectedVote = vote;
            ['A', 'tie', 'B', 'both_bad'].forEach(v => {
                const btn = document.getElementById('btn-' + v);
                if (btn) btn.className = v === vote ? 'active' : '';
            });
        }

        async function submitVote(id, subsetId) {
            if (!selectedVote) {
                alert('Bitte wähle eine Option!');
                return;
            }
            
            try {
                const resp = await fetch(API + '/arena/vote', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Session-ID': sessionId || ensureSessionId()
                    },
                    body: JSON.stringify({
                        comparison_id: id,
                        vote: selectedVote,
                        comment: null,
                        subset_id: subsetId || assignedSubset
                    })
                });
                
                if (resp.ok) {
                    selectedVote = null;
                    votedSet.add(String(id));
                    votedInSubset = comparisons.filter(c => votedSet.has(String(c.id))).length;
                    await load();
                } else {
                    alert('❌ Fehler: ' + resp.statusText);
                }
            } catch (e) {
                alert('❌ Fehler: ' + e.message);
            }
        }

        function resetSession() {
            if (confirm('Möchtest du wirklich von vorne beginnen? Deine bisherigen Votes bleiben gespeichert, aber du bekommst eine neue Session-ID.')) {
                localStorage.removeItem('arena_session_id');
                localStorage.removeItem('arena_subset');
                votedSet.clear();
                location.reload();
            }
        }

        // Start immediately
        load();
        
        // Timeout fallback
        setTimeout(function() {
            if (comparisons.length === 0 && assignedSubset === null) {
                document.getElementById('container').innerHTML = 
                    '<div class="error">⚠️ Timeout beim Laden<br>' +
                    'API: <a href="http://127.0.0.1:8001/arena/comparisons" target="_blank">http://127.0.0.1:8001/arena/comparisons</a><br>' +
                    'Prüfe Browser Console für Details</div>';
            }
        }, 5000);
    </script>
</body>
</html>
"""
    return html.replace("__API_OVERRIDE__", api_override)


@app.get("/user-votes", response_class=HTMLResponse)
def user_votes():
    """User-Votes mit Session-IDs"""
    api_base = os.getenv("ARENA_API_BASE", "http://arena-api:8001").rstrip("/")
    api_override = api_base.replace("http://arena-api:", "http://localhost:")
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset=\"UTF-8\">
    <title>User Votes - Arena</title>
    <style>
        body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0 auto; max-width: 1400px; padding: 24px; background: #f6f6f6; color: #1f1f1f; }
        h1 { margin: 0 0 12px; font-weight: 600; }
        .controls { display: flex; gap: 10px; align-items: center; margin: 12px 0 16px; }
        input, button { padding: 8px 10px; border: 1px solid #d0d0d0; border-radius: 4px; background: #fff; }
        table { width: 100%; border-collapse: collapse; background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
        th, td { padding: 10px 12px; border-bottom: 1px solid #eee; text-align: left; vertical-align: top; }
        th { background: #fafafa; font-weight: 600; position: sticky; top: 0; }
        tbody tr:hover { background: #fafafa; }
        .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; border: 1px solid #ddd; font-size: 12px; }
        .vote-A { background:#eef6ff; border-color:#cfe3ff; }
        .vote-B { background:#f4e8ff; border-color:#e3d3ff; }
        .vote-tie { background:#eef7ee; border-color:#d7ead7; }
        .vote-both_bad { background:#ffe8e8; border-color:#ffcccc; }
        .muted { color:#666; font-size:12px; }
        .nowrap { white-space: nowrap; }
        .session { font-family: monospace; font-size: 11px; background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }
    </style>
    <script>
        const API_OVERRIDE = "__API_OVERRIDE__";
        const API = (API_OVERRIDE && API_OVERRIDE.trim() !== "")
            ? API_OVERRIDE.replace(/\/$/, '')
            : (window.location.port === "8002"
                ? window.location.origin.replace(":8002", ":8001").replace(/\/$/, '')
                : window.location.origin.replace(/\/$/, ''));
        let allVotes = [];
        let filtered = [];

        async function load() {
            const status = document.getElementById('status');
            const url = `${API}/arena/user-votes`;
            status.textContent = 'Lade von ' + url;
            try {
                const resp = await fetch(url);
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                const data = await resp.json();
                allVotes = data.votes || [];
                applyFilters();
                status.textContent = allVotes.length + ' User-Votes geladen';
            } catch (e) {
                status.textContent = '❌ Fehler: ' + e.message;
            }
        }

        function applyFilters() {
            const q = (document.getElementById('search').value || '').toLowerCase();
            filtered = allVotes.filter(v => {
                const text = ((v.session_id||'') + ' ' + (v.comparison_id||'')).toLowerCase();
                return !q || text.includes(q);
            });
            renderTable();
        }

        function pill(vote) {
            if (!vote) return '<span class="pill">-</span>';
            const cls = vote === 'A' ? 'vote-A' : vote === 'B' ? 'vote-B' : vote === 'tie' ? 'vote-tie' : 'vote-both_bad';
            const label = vote === 'both_bad' ? 'Beide schlecht' : vote;
            return `<span class="pill ${cls}">${label}</span>`;
        }

        function renderTable() {
            const tbody = document.querySelector('tbody');
            tbody.innerHTML = filtered.map(v => `
                <tr>
                    <td class="nowrap muted">${(v.timestamp||'').replace('T',' ')}</td>
                    <td><span class="session" title="${v.session_id}">${(v.session_id||'').slice(0,8)}...</span></td>
                    <td class="muted" style="font-size:11px;" title="${v.comparison_id}">${(v.comparison_id||'').slice(0,12)}...</td>
                    <td>${pill(v.vote)}</td>
                    <td class="muted">${v.subset_id || '-'}</td>
                    <td class="muted">${v.comment || ''}</td>
                </tr>
            `).join('');
            document.getElementById('status').textContent = filtered.length + ' von ' + allVotes.length + ' Votes angezeigt';
        }

        function exportCSV() {
            const header = ['timestamp','session_id','comparison_id','vote','subset_id','comment'];
            const rows = filtered.map(v => header.map(h => {
                let val = (v[h] || '').toString().split('\\n').join(' ').split('"').join('""');
                return val;
            }));
            const csv = [header.join(','), ...rows.map(r => '"' + r.join('","') + '"')].join('\\n');
            const blob = new Blob([csv], {type:'text/csv'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'user_votes.csv';
            a.click();
            URL.revokeObjectURL(url);
        }

        window.addEventListener('DOMContentLoaded', load);
    </script>
</head>
<body>
    <h1>User Votes (Session-basiert)</h1>
    <div class="controls">
        <span id="status" class="muted">-</span>
        <input id="search" type="search" placeholder="Suche Session/Comparison-ID" oninput="applyFilters()"/>
        <button onclick="exportCSV()">CSV Export</button>
        <a href="/results" style="margin-left:auto;padding:8px 12px;text-decoration:none;background:#fff;border:1px solid #d0d0d0;border-radius:4px;">← Zurück zu Ergebnissen</a>
    </div>
    <table>
        <thead>
            <tr>
                <th>Timestamp</th>
                <th>Session-ID</th>
                <th>Comparison-ID</th>
                <th>Vote</th>
                <th>Subset</th>
                <th>Kommentar</th>
            </tr>
        </thead>
        <tbody>
            <tr><td colspan="6" class="muted">Lade…</td></tr>
        </tbody>
    </table>
</body>
</html>
"""
    return html.replace("__API_OVERRIDE__", api_override)


@app.get("/results", response_class=HTMLResponse)
def results():
    """Neutrale, read-only Ergebnisliste als Tabelle"""
    api_base = os.getenv("ARENA_API_BASE", "http://arena-api:8001").rstrip("/")
    # Convert internal Docker DNS to localhost for browser access
    api_override = api_base.replace("http://arena-api:", "http://localhost:")
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset=\"UTF-8\">
    <title>Arena Ergebnisse</title>
    <style>
        body { font-family: system-ui, -apple-system, \"Segoe UI\", sans-serif; margin: 0 auto; max-width: 1200px; padding: 24px; background: #f6f6f6; color: #1f1f1f; }
        h1 { margin: 0 0 12px; font-weight: 600; }
        .controls { display: flex; gap: 10px; align-items: center; margin: 12px 0 16px; }
        select, button, input { padding: 8px 10px; border: 1px solid #d0d0d0; border-radius: 4px; background: #fff; }
        table { width: 100%; border-collapse: collapse; background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
        th, td { padding: 10px 12px; border-bottom: 1px solid #eee; text-align: left; vertical-align: top; }
        th { background: #fafafa; font-weight: 600; position: sticky; top: 0; }
        tbody tr:hover { background: #fafafa; }
        .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; border: 1px solid #ddd; font-size: 12px; }
        .vote-A { background:#eef6ff; border-color:#cfe3ff; }
        .vote-B { background:#f4e8ff; border-color:#e3d3ff; }
        .vote-tie { background:#eef7ee; border-color:#d7ead7; }
        .vote-both_bad { background:#ffe8e8; border-color:#ffcccc; }
        .muted { color:#666; font-size:12px; }
        .nowrap { white-space: nowrap; }
        .q { max-width: 420px; }
        .ans { max-width: 460px; }
    </style>
    <script>
        // API base: allow override for direct UI (8002) vs. nginx proxy
        const API_OVERRIDE = "__API_OVERRIDE__";
        const API = (API_OVERRIDE && API_OVERRIDE.trim() !== "")
            ? API_OVERRIDE.replace(/\/$/, '')
            : (window.location.port === "8002"
                ? window.location.origin.replace(":8002", ":8001").replace(/\/$/, '')
                : window.location.origin.replace(/\/$/, ''));
        let all = [];
        let filtered = [];
        let currentSubset = 'all';

        async function load() {
            const container = document.getElementById('status');
            const subsetSel = document.getElementById('subset');
            const subset = subsetSel ? subsetSel.value : 'all';
            currentSubset = subset;
            const url = subset === 'all' ? `${API}/arena/comparisons` : `${API}/arena/comparisons?subset=${subset}`;
            container.textContent = 'Lade von ' + url;
            console.log('Starting load from:', url);
            console.log('API base:', API);
            try {
                console.log('Fetching from:', url);
                const resp = await fetch(url, {
                    method: 'GET',
                    headers: {'Accept': 'application/json'},
                    mode: 'cors'
                });
                console.log('Response status:', resp.status);
                console.log('Response headers:', [...resp.headers.entries()]);
                
                if (!resp.ok) {
                    const errorText = await resp.text();
                    console.error('Response not OK:', resp.status, errorText);
                    throw new Error('HTTP ' + resp.status + ': ' + resp.statusText + ' - ' + errorText);
                }
                
                const data = await resp.json();
                console.log('Data received:', data);
                console.log('Comparisons count:', data.comparisons ? data.comparisons.length : 0);
                
                all = data.comparisons || [];
                console.log('Loaded comparisons:', all.length);
                
                applyFilters();
                const subsetLabel = subset === 'all' ? 'alle Subsets' : 'Subset ' + subset;
                container.textContent = all.length + ' Vergleiche geladen (' + subsetLabel + ')';
            } catch (e) {
                console.error('Load error:', e);
                container.textContent = '❌ Fehler: ' + e.message + ' | API: ' + API;
            }
        }

        function applyFilters() {
            const sel = document.getElementById('filter');
            const q = (document.getElementById('search').value || '').toLowerCase();
            filtered = all.filter(c => {
                const voted = !!c.vote;
                const voteOk = sel.value === 'all' || (sel.value === 'voted' && voted) || (sel.value === 'unvoted' && !voted);
                const text = ((c.question||'') + ' ' + (c.answer_a||'') + ' ' + (c.answer_b||'')).toLowerCase();
                const searchOk = !q || text.includes(q);
                return voteOk && searchOk;
            });
            renderTable();
        }

        function pill(vote) {
            if (!vote) return '<span class="pill">-</span>';
            const cls = vote === 'A' ? 'vote-A' : vote === 'B' ? 'vote-B' : vote === 'tie' ? 'vote-tie' : 'vote-both_bad';
            const label = vote === 'both_bad' ? 'Beide schlecht' : vote;
            return `<span class="pill ${cls}">${label}</span>`;
        }

        function truncate(t, n=140) { if (!t) return ''; return t.length>n ? t.slice(0,n)+'…' : t; }

        function renderTable() {
            const tbody = document.querySelector('tbody');
            tbody.innerHTML = filtered.map(c => `
                <tr>
                    <td class="nowrap muted">${(c.timestamp||'').replace('T',' ')}</td>
                    <td class="q">${truncate(c.question, 160)}</td>
                    <td class="ans">
                        <strong style="color: #444; font-weight: 600;">${(c.actual_model_a || c.model_a || 'Modell A').substring(0, 30)}</strong><br>
                        ${truncate(c.actual_answer_a || c.answer_a, 160)}
                    </td>
                    <td class="ans">
                        <strong style="color: #444; font-weight: 600;">${(c.actual_model_b || c.model_b || 'Modell B').substring(0, 30)}</strong><br>
                        ${truncate(c.actual_answer_b || c.answer_b, 160)}
                    </td>
                    <td>${pill(c.vote)}</td>
                    <td class="nowrap muted">${c.vote_timestamp ? c.vote_timestamp.replace('T',' ') : ''}</td>
                    <td class="nowrap muted">${c.subset_id || (currentSubset !== 'all' ? currentSubset : '-')}</td>
                </tr>
            `).join('');
            const status = document.getElementById('status');
            if (status) status.textContent = filtered.length + ' von ' + all.length + ' Einträgen angezeigt';
        }


        function exportCSV() {
            const header = ['id','timestamp','question','actual_model_a','actual_answer_a','actual_model_b','actual_answer_b','vote','vote_timestamp','subset_id'];
            const rows = filtered.map(c => header.map(h => {
                let val = (c[h] || '').toString();
                val = val.split('\\n').join(' ');
                val = val.split('"').join('""');
                return val;
            }));
            const csv = [header.join(','), ...rows.map(r => '"' + r.join('","') + '"')].join('\\n');
            const blob = new Blob([csv], {type:'text/csv;charset=utf-8;'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'arena_results.csv';
            a.click();
            URL.revokeObjectURL(url);
        }

        window.addEventListener('DOMContentLoaded', load);
    </script>
</head>
<body>
    <h1>Arena Ergebnisse</h1>
    <div class="controls">
        <span id="status" class="muted">-</span>
        <select id="subset" onchange="load()">
            <option value="all">Alle Subsets</option>
            <option value="1">Subset 1</option>
            <option value="2">Subset 2</option>
            <option value="3">Subset 3</option>
            <option value="4">Subset 4</option>
        </select>
        <select id="filter" onchange="applyFilters()">
            <option value="all">Alle</option>
            <option value="voted">Nur gevotet</option>
            <option value="unvoted">Nur offen</option>
        </select>
        <input id="search" type="search" placeholder="Suche in Frage/Antworten" oninput="applyFilters()"/>
        <button onclick="exportCSV()">CSV Export</button>
        <a href="/user-votes" style="margin-left:auto;padding:8px 12px;text-decoration:none;background:#4a90e2;color:white;border-radius:4px;">👥 User-Votes ansehen</a>
    </div>
    <table>
        <thead>
            <tr>
                <th>Erstellt</th>
                <th>Frage</th>
                <th>Antwort A (Modell + Text)</th>
                <th>Antwort B (Modell + Text)</th>
                <th>Vote</th>
                <th>Vote-Zeit</th>
                <th>Subset</th>
            </tr>
        </thead>
        <tbody>
            <tr><td colspan="7" class="muted">Lade…</td></tr>
        </tbody>
    </table>
</body>
</html>
"""
    return html.replace("__API_OVERRIDE__", api_override)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
