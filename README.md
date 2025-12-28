# Dependencies
- python 3.11
- poetry 1.7.1 & `poetry install`
- task: `brew install go-task`
- install pre-commit hooks: [`pre-commit`](https://github.com/pre-commit/pre-commit) `install`

# Local development

## VectorDB [Qdrant](https://github.com/qdrant/qdrant-client)
`docker pull qdrant/qdrant:v1.6.1`
`docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage:z qdrant/qdrant:v1.6.1`

`client = QdrantClient(host =QDRANT_URL, api_key=QDRANT_TOKEN, port=6333, grpc_port=6334 , https=False, prefer_grpc=True)`

## Run frontent: streamlit
Go into the src/frontend folder and run:
`streamlit run frontend.py`

## Docker

### Deployment (Containers)
- Overview: The Arena API and lightweight Voting UI are containerized and orchestrated via [docker-compose.prod.yml](docker-compose.prod.yml). Images are built from [Dockerfile.api](Dockerfile.api) and [Dockerfile.ui](Dockerfile.ui), fronted by Nginx ([nginx/nginx.conf](nginx/nginx.conf)).
- Data: Votes persist in the `arena_data` volume as `/data/arena_votes.jsonl` inside the API container.
- Config: Use [.env.prod.example](.env.prod.example) as a template; create `.env` or `.env.prod` with real values.

#### Quick Start (Local)
```zsh
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps

# Health checks
curl -fsS http://127.0.0.1:8001/health
curl -fsS http://127.0.0.1:8002/ | head -1

# Stats
curl -fsS http://127.0.0.1:8001/arena/statistics | python -m json.tool | head -20
```

#### Access
- API (local): http://127.0.0.1:8001
- Voting UI (local): http://127.0.0.1:8002/

#### Operations
```zsh
# Logs
docker compose -f docker-compose.prod.yml logs -f arena-api arena-ui

# Restart services
docker compose -f docker-compose.prod.yml restart arena-api arena-ui

# Stop / remove
docker compose -f docker-compose.prod.yml down --remove-orphans

# Rebuild after code changes
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

#### Scripts (optional helpers)
- Deploy lifecycle: [scripts/deploy.sh](scripts/deploy.sh)
    - `./scripts/deploy.sh deploy` builds, restarts, runs health checks.
- Backups: [scripts/backup.sh](scripts/backup.sh)
    - Creates dated JSONL backups under `/var/backups/arena` and prunes by retention.
- Monitoring: [scripts/healthcheck.sh](scripts/healthcheck.sh)
    - Checks API/UI health, Docker status, disk usage, prints stats.

#### Configuration Notes
- Secrets: Do not commit `.env`. Prefer environment variables or Azure Key Vault.
- NLTK: Container preloads `punkt_tab` and sets `NLTK_DATA=/tmp/nltk_data` for LlamaIndex.
- Rate limiting: Enabled for `/arena/*` routes in Nginx. Adjust in [nginx/nginx.conf](nginx/nginx.conf).
- Fixed questions (Arena/RAGAS): [data/fixed_questions.txt](data/fixed_questions.txt) ist der verbindliche Katalog. Seeder lokal: `python scripts/arena_seed_with_llm.py --input data/fixed_questions.txt --api-url http://127.0.0.1:8001`. Im Container: Datei ins API-Container-Volume kopieren (`docker cp data/fixed_questions.txt fu-arena-api:/app/data/`) und mit `--input /app/data/fixed_questions.txt` seeden.

#### Production Follow-ups
- TLS certificates: Place `fullchain.pem` and `privkey.pem` in `nginx/ssl/` for HTTPS.
- DNS: Point your domain to the host running the stack; update CORS in `.env`.
- VM: Install Docker + Compose, copy repo, run `deploy.sh deploy`.
- Observability: Add alerts (email/Slack), schedule backups via cron.

## How to build and run Image
`docker login` <br />
`docker build -t fatemeh001/kicampus_chatbot:0.0.1 .` <br />
`docker images` <br />
`docker run -p 8501 fatemeh001/kicampus_chatbot:0.0.1` <br />

`docker login kicwaacrdev.azurecr.io` <br />
`docker tag fatemeh001/kicamp_chatbot:0.0.1 kicwaacrdev.azurecr.io/fatemeh001/kicampus_chatbot:0.0.1` <br />
`docker push kicwaacrdev.azurecr.io/fatemeh001/kicampus_chatbot:0.0.1` <br />

## To run docker images locally, mount your credentials:
`docker run -it --rm -p 80:80 -v ~/.azure:/home/appuser/.azure kicwaacrdev.azurecr.io/rest-api:latest`

### Build and push Docker images locally
Before pushing the docker image you need to be authenticated docker via `gcloud auth configure-docker europe-west3-docker.pkg.dev`.

If you're working with a mac that is using an arm64 architecture, you specifically need to build a docker image based on an [amd architecture for cloud run](https://stackoverflow.com/questions/66920645/exec-format-error-when-running-containers-build-with-apple-m1-chip-arm-based).

# Arena Voting (UI + Results)

Lightweight, local-only Arena mode to compare answers and record votes.

- Code:
    - UI and Results: `src/openwebui/voting_ui_simple.py`
    - Lightweight Arena API: `src/openwebui/arena_api.py`
    - Storage (append-only JSONL): `src/openwebui/data/arena_votes.jsonl` (not committed)

## Run locally (two processes)

Start the API (arena endpoints only):

```zsh
/Users/browse/FU_Chatbot_RD_Zitho/.venv/bin/python -m uvicorn src.openwebui.arena_api:app --host 127.0.0.1 --port 8001
```

Start the UI (voting + results dashboard):

```zsh
/Users/browse/FU_Chatbot_RD_Zitho/.venv/bin/python -m uvicorn src.openwebui.voting_ui_simple:app --host 127.0.0.1 --port 8002
```

Open in browser:

- Voting UI: http://127.0.0.1:8002/
- Results dashboard: http://127.0.0.1:8002/results (filters, search, CSV export)

## API surface (used by UI)

- `GET  /arena/comparisons` – list comparisons
- `GET  /arena/statistics` – aggregate stats (backend-only)
- `GET  /arena/comparison/{id}` – one comparison
- `POST /arena/save-comparison` – create new comparison
- `POST /arena/vote` – record a vote `{comparison_id, vote: "A"|"B"|"tie", comment?}`

## Notes & Troubleshooting

- Use `127.0.0.1` explicitly (not `localhost`) to avoid Safari localhost quirks.
- The results page shows live status messages and logs to the browser console on errors.
- CSV export escapes quotes and replaces newlines for Excel/Sheets compatibility.
- Data is stored in `src/openwebui/data/arena_votes.jsonl`; keep it out of commits.
- If results show "Lade…" endlessly: verify API is up and `GET /arena/comparisons` returns data.
- If Safari reports JS syntax errors, ensure you’re on branch `feature/openwebui-arena` (contains fixes for newline/quote escaping and missing elements).

## Seeding comparisons

You can seed via the API (`POST /arena/save-comparison`) or the helper script `scripts/arena_seed.py` which appends unvoted items directly to the JSONL. Unvoted rows appear in the voting UI automatically.

Examples:

```zsh
# From a newline-separated questions file
python scripts/arena_seed.py --questions path/to/questions.txt

# From a JSON array (objects require: question, answer_a, answer_b; optional: model_a, model_b)
python scripts/arena_seed.py --json path/to/items.json

# Custom storage file and placeholders
python scripts/arena_seed.py \
    --questions questions.txt \
    --model-a "kicampus-original" --model-b "kicampus-improved" \
    --answer-a "Antwort A für: {q}" --answer-b "Antwort B für: {q}" \
    --storage-file src/openwebui/data/arena_votes.jsonl

# Dry-run to preview
python scripts/arena_seed.py --questions questions.txt --dry-run
```

# Data Extraction

# Moodle
To access content from Moodle, you need access to Moodle courses via the REST API. To set up the integration, do the following steps:
0. Get admin access to moodle.
1. Enable Web Services: _Site Administration_ -> _General_ -> _Advanced Features_ -> _Enable web services_
2. Enable REST Protocol: _Site Administration_ -> _Server_ -> _Web Services_ -> _Manage Protocols_ -> _Enable REST protocol_
3. (Optional): Create a technical new user/roles
4. Create a new external service _Site Administration_ -> _Server_ -> _External services_. Give it a name and enable _Enabled_, _Authorized users only_ and _Can download files_ (under _Show more..._).
5. Add the user as an _Authorised User_ to the external service.
6. Add the following functions to the external service:
    - core_block_get_course_blocks
    - core_course_get_categories
    - core_course_get_contents
    - core_course_get_course_content_items
    - core_course_get_course_module
    - core_course_get_courses
    - core_course_get_module
7. Create a token for the user and external service under _Site Administration_ -> _Server_ -> _Manage tokens_. This allows you to authenticate against the REST API.

You can try it out with a GET request against this url (swap TOKEN for your token und FUNCTION against the function to test):
https://ki-campus-test.fernuni-hagen.de/webservice/rest/server.php?wstoken=TOKEN&wsfunction=FUNCTION&moodlewsrestformat=json
