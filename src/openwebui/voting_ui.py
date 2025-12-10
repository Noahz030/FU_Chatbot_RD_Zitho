"""
Arena Voting Web UI

Eine standalone Web-Anwendung für Arena Voting.
Läuft auf Port 8002 und integriert sich mit der OpenWebUI Arena.

Features:
- Live Vergleiche aus OpenWebUI Arena abrufen
- Voting Buttons für jede Antwort
- Statistik Dashboard
- Export Funktionen
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import json
from pathlib import Path

from src.openwebui.voting_system import default_storage

app = FastAPI(
    title="Arena Voting UI",
    description="Web UI für Arena Voting und Benchmarking",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def get_voting_dashboard():
    """Hauptseite mit Voting Dashboard."""
    return """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏆 KI-Campus Arena Voting</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        
        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .stat-card h3 {
            color: #667eea;
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 10px;
            opacity: 0.7;
        }
        
        .stat-card .value {
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
        }
        
        .comparisons-section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        }
        
        .comparisons-section h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        
        .comparison-card {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            background: #f9f9f9;
        }
        
        .comparison-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .comparison-header h3 {
            color: #333;
            font-size: 1.1em;
        }
        
        .vote-badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9em;
        }
        
        .vote-badge.a { background: #e3f2fd; color: #1976d2; }
        .vote-badge.b { background: #f3e5f5; color: #7b1fa2; }
        .vote-badge.tie { background: #f5f5f5; color: #616161; }
        .vote-badge.unvoted { background: #fff3e0; color: #f57c00; }
        
        .answers {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .answer {
            background: white;
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid #ccc;
            font-size: 0.95em;
            line-height: 1.5;
            color: #555;
        }
        
        .answer.a { border-left-color: #1976d2; }
        .answer.b { border-left-color: #7b1fa2; }
        
        .vote-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        
        .vote-buttons button {
            flex: 1;
            padding: 10px;
            border: 2px solid #e0e0e0;
            background: white;
            color: #666;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s;
        }
        
        .vote-buttons button:hover {
            background: #f5f5f5;
            border-color: #667eea;
        }
        
        .vote-buttons button.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        
        .comment-input {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 0.9em;
            margin-bottom: 10px;
        }
        
        .submit-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
        }
        
        .submit-btn:hover {
            background: #5568d3;
        }
        
        .submit-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .success-msg {
            padding: 10px;
            background: #c8e6c9;
            color: #2e7d32;
            border-radius: 4px;
            margin-bottom: 10px;
            display: none;
        }
        
        .success-msg.show {
            display: block;
        }
        
        .no-data {
            text-align: center;
            padding: 40px 20px;
            color: #999;
        }
        
        @media (max-width: 768px) {
            .answers {
                grid-template-columns: 1fr;
            }
            
            header h1 {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏆 KI-Campus Arena Voting</h1>
            <p>Vergleiche und bewerte die beiden Chatbot-Versionen</p>
        </header>
        
        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <h3>Insgesamt</h3>
                <div class="value">-</div>
            </div>
            <div class="stat-card">
                <h3>Gevotet</h3>
                <div class="value">-</div>
            </div>
            <div class="stat-card">
                <h3>Model B führt</h3>
                <div class="value">-</div>
            </div>
            <div class="stat-card">
                <h3>Unentschieden</h3>
                <div class="value">-</div>
            </div>
        </div>
        
        <div class="comparisons-section">
            <h2>Vergleiche zum Bewerten</h2>
            <div id="comparisonsContainer">
                <div class="no-data">Lade Vergleiche...</div>
            </div>
        </div>
    </div>
    
    <script>
        const API_BASE = 'http://localhost:8001';
        
        async function loadComparisons() {
            try {
                const response = await fetch(`${API_BASE}/arena/comparisons`);
                const data = await response.json();
                renderComparisons(data.comparisons);
                updateStats();
            } catch (error) {
                console.error('Error loading comparisons:', error);
                document.getElementById('comparisonsContainer').innerHTML = 
                    '<div class="no-data">❌ Fehler beim Laden der Vergleiche</div>';
            }
        }
        
        function renderComparisons(comparisons) {
            const container = document.getElementById('comparisonsContainer');
            
            if (comparisons.length === 0) {
                container.innerHTML = '<div class="no-data">📭 Keine Vergleiche vorhanden</div>';
                return;
            }
            
            container.innerHTML = comparisons.reverse().map(comp => {
                const voted = comp.vote ? `✓ gevotet: ${comp.vote}` : '⏳ ausstehend';
                const voteBadgeClass = comp.vote ? comp.vote.toLowerCase() : 'unvoted';
                
                return `
                    <div class="comparison-card">
                        <div class="comparison-header">
                            <h3>❓ ${comp.question}</h3>
                            <div class="vote-badge ${voteBadgeClass}">${voted}</div>
                        </div>
                        
                        <div class="answers">
                            <div class="answer a">
                                <strong>Model A (Original)</strong><br>
                                ${comp.answer_a.substring(0, 300)}...
                            </div>
                            <div class="answer b">
                                <strong>Model B (Verbessert)</strong><br>
                                ${comp.answer_b.substring(0, 300)}...
                            </div>
                        </div>
                        
                        ${!comp.vote ? `
                            <div class="vote-buttons" data-comparison-id="${comp.id}">
                                <button class="vote-btn" data-vote="A">👈 Model A</button>
                                <button class="vote-btn" data-vote="tie">🤝 Unentschieden</button>
                                <button class="vote-btn" data-vote="B">👉 Model B</button>
                            </div>
                            <input type="text" class="comment-input" placeholder="Optional: Kommentar..." data-comparison-id="${comp.id}">
                            <button class="submit-btn" onclick="submitVote('${comp.id}')">Vote abgeben</button>
                            <div class="success-msg" data-comparison-id="${comp.id}"></div>
                        ` : `
                            <p><strong>Dein Vote:</strong> ${comp.vote === 'A' ? 'Model A' : comp.vote === 'B' ? 'Model B' : 'Unentschieden'}</p>
                            ${comp.comment ? `<p><strong>Kommentar:</strong> ${comp.comment}</p>` : ''}
                        `}
                    </div>
                `;
            }).join('');
            
            // Attach event listeners
            document.querySelectorAll('.vote-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const parent = this.parentElement;
                    parent.querySelectorAll('.vote-btn').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    this.parentElement.dataset.selectedVote = this.dataset.vote;
                });
            });
        }
        
        async function submitVote(comparisonId) {
            const buttons = document.querySelector(`[data-comparison-id="${comparisonId}"]`);
            const vote = buttons.dataset.selectedVote;
            const comment = document.querySelector(`[data-comparison-id="${comparisonId}"].comment-input`)?.value;
            
            if (!vote) {
                alert('Bitte wähle eine Option');
                return;
            }
            
            try {
                const response = await fetch(`${API_BASE}/arena/vote`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({comparison_id: comparisonId, vote, comment: comment || null})
                });
                
                if (response.ok) {
                    const msgEl = document.querySelector(`[data-comparison-id="${comparisonId}"].success-msg`);
                    msgEl.textContent = '✅ Vote gespeichert!';
                    msgEl.classList.add('show');
                    setTimeout(() => loadComparisons(), 1000);
                } else {
                    alert('❌ Fehler beim Vote');
                }
            } catch (error) {
                console.error('Vote error:', error);
                alert('❌ Fehler beim Vote: ' + error.message);
            }
        }
        
        async function updateStats() {
            try {
                const response = await fetch(`${API_BASE}/arena/statistics`);
                const stats = await response.json();
                
                const cards = document.querySelectorAll('.stat-card .value');
                cards[0].textContent = stats.total_comparisons;
                cards[1].textContent = stats.voted;
                cards[2].textContent = `${(stats.win_rate_b * 100).toFixed(1)}%`;
                cards[3].textContent = `${(stats.tie_rate * 100).toFixed(1)}%`;
            } catch (error) {
                console.error('Error updating stats:', error);
            }
        }
        
        // Load on startup
        loadComparisons();
        setInterval(loadComparisons, 5000); // Refresh every 5 seconds
    </script>
</body>
</html>
"""


@app.get("/stats", response_class=JSONResponse)
def get_stats():
    """JSON API für Statistiken."""
    stats = default_storage.get_statistics()
    return stats


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
