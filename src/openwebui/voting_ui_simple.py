"""
Vereinfachtes Arena Voting UI - direkt und einfach
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_BASE = "http://localhost:8001"

@app.get("/", response_class=HTMLResponse)
def index():
    """Einfaches Voting UI"""
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Arena Voting</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: #f0f0f0;
        }
        h1 { color: #333; }
        .stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin: 20px 0;
        }
        .stat {
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            font-size: 12px;
            margin-top: 5px;
        }
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
            background: #f9f9f9;
            border-left: 4px solid #ddd;
            border-radius: 4px;
            font-size: 13px;
            line-height: 1.5;
        }
        .answer.a { border-left-color: #1976d2; }
        .answer.b { border-left-color: #7b1fa2; }
        .buttons {
            display: flex;
            gap: 10px;
            margin: 15px 0;
        }
        button {
            flex: 1;
            padding: 10px;
            border: 2px solid #ddd;
            background: white;
            cursor: pointer;
            border-radius: 4px;
            font-weight: bold;
        }
        button:hover { background: #f0f0f0; }
        button.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        .submit {
            width: 100%;
            background: #28a745;
            color: white;
            border: none;
        }
        .submit:hover { background: #218838; }
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
    <h1>🏆 KI-Campus Arena Voting</h1>
    
    <div class="stats" id="stats">
        <div class="stat"><div class="stat-value">-</div><div class="stat-label">Total</div></div>
        <div class="stat"><div class="stat-value">-</div><div class="stat-label">Gevotet</div></div>
        <div class="stat"><div class="stat-value">-</div><div class="stat-label">Model B %</div></div>
        <div class="stat"><div class="stat-value">-</div><div class="stat-label">Ties %</div></div>
    </div>
    
    <div id="container">
        <div class="loading">⏳ Lade Vergleiche...</div>
    </div>

    <script>
        const API = 'http://localhost:8001';
        let comparisons = [];
        let currentIndex = 0;
        let selectedVote = null;

        async function load() {
            try {
                const resp = await fetch(API + '/arena/comparisons');
                const data = await resp.json();
                comparisons = data.comparisons;
                
                // Stats aktualisieren
                const stats = await fetch(API + '/arena/statistics').then(r => r.json());
                document.querySelectorAll('.stat-value').forEach((el, i) => {
                    if (i === 0) el.textContent = stats.total_comparisons;
                    if (i === 1) el.textContent = stats.voted;
                    if (i === 2) el.textContent = (stats.win_rate_b * 100).toFixed(0) + '%';
                    if (i === 3) el.textContent = (stats.tie_rate * 100).toFixed(0) + '%';
                });
                
                render();
            } catch (e) {
                document.getElementById('container').innerHTML = 
                    '<div class="error">❌ Fehler: ' + e.message + '</div>';
            }
        }

        function render() {
            const container = document.getElementById('container');
            const unvoted = comparisons.filter(c => !c.vote);
            
            if (unvoted.length === 0) {
                container.innerHTML = '<div class="loading">✅ Alle Vergleiche abgestimmt!</div>';
                return;
            }
            
            const comp = unvoted[0];
            selectedVote = null;
            
            container.innerHTML = `
                <div class="comparison">
                    <h2>❓ ${comp.question}</h2>
                    <div class="answers">
                        <div class="answer a">
                            <strong>Model A (Original)</strong><br>
                            ${comp.answer_a.substring(0, 250)}...
                        </div>
                        <div class="answer b">
                            <strong>Model B (Verbessert)</strong><br>
                            ${comp.answer_b.substring(0, 250)}...
                        </div>
                    </div>
                    <div class="buttons">
                        <button onclick="selectVote('A')" id="btn-A">👈 Model A</button>
                        <button onclick="selectVote('tie')" id="btn-tie">🤝 Tie</button>
                        <button onclick="selectVote('B')" id="btn-B">👉 Model B</button>
                    </div>
                    <button class="submit" onclick="submitVote('${comp.id}')">✅ Vote abgeben</button>
                </div>
            `;
        }

        function selectVote(vote) {
            selectedVote = vote;
            ['A', 'tie', 'B'].forEach(v => {
                const btn = document.getElementById('btn-' + v);
                if (btn) btn.className = v === vote ? 'active' : '';
            });
        }

        async function submitVote(id) {
            if (!selectedVote) {
                alert('Bitte wähle eine Option!');
                return;
            }
            
            try {
                const resp = await fetch(API + '/arena/vote', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        comparison_id: id,
                        vote: selectedVote,
                        comment: null
                    })
                });
                
                if (resp.ok) {
                    alert('✅ Vote gespeichert!');
                    load();
                } else {
                    alert('❌ Fehler: ' + resp.statusText);
                }
            } catch (e) {
                alert('❌ Fehler: ' + e.message);
            }
        }

        // Start
        load();
        setInterval(load, 5000);
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
