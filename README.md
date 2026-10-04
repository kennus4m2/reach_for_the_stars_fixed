# Reach for the Stars API

CS 313 Library Game Hub. FastAPI + PostgreSQL. Follows Hub Contract v1.

## Setup
1. Make sure PostgreSQL is running (Services > postgresql-x64-xx > Running).
2. In pgAdmin, create a database named `reach_for_the_stars`.
3. Open its Query Tool and run `docs/schema.sql` (safe to run again).
4. Copy `.env.example` to `.env`. Fill in `DB_PASSWORD`, `JWT_SECRET`, `TEAM_NAME`.
5. Install packages:  `py -m pip install -r requirements.txt`
6. Create a host account:  `py -m scripts.create_host`

## Run
    py main.py

API docs you can click and test: http://localhost:3001/docs

## How a game works
1. Host logs in, creates a question set, then a session (gets a 6-digit join code).
2. Players join with a nickname (no account) and get a player token.
3. Host starts the session (PATCH status=playing). The round timer starts.
4. Each player: GET next question, POST answer, repeat.
   Every 5th correct answer in a row offers 3 mystery chests: POST a chest pick.
5. Host ends the session (or time runs out). Leaderboard stays saved.

## Endpoints (all start with /api/v1)
| Verb | URL | What it does | Token | Success | Errors |
|---|---|---|---|---|---|
| GET | /game-info | Hub reads game details | No | 200 | 500 |
| GET | /health | API and database check | No | 200 | 503 |
| POST | /auth/login | Host logs in | No | 200 | 400, 401 |
| POST | /question-sets | Create a question set | Host | 201 | 400, 401 |
| GET | /question-sets | List my sets | Host | 200 | 401 |
| GET | /question-sets/{id} | Read one set (with answers) | Host | 200 | 401, 403, 404 |
| PUT | /question-sets/{id} | Replace a set | Host | 200 | 400, 401, 403, 404, 409 |
| DELETE | /question-sets/{id} | Delete a set | Host | 200 | 401, 403, 404, 409 |
| POST | /sessions | Start a game, get join code | Host | 201 | 400, 401, 403, 404 |
| GET | /sessions | List my games | Host | 200 | 401 |
| GET | /sessions/{code} | Game status | No | 200 | 404 |
| PATCH | /sessions/{code} | Start or end a game | Host | 200 | 400, 401, 403, 404, 409 |
| POST | /sessions/{code}/players | Player joins | No | 201 | 400, 404, 409 |
| GET | /sessions/{code}/players/me | My stars, lives, streak, rank | Player | 200 | 401, 403, 404 |
| GET | /sessions/{code}/questions/next | Next question (no answer) | Player | 200 | 401, 403, 404, 409 |
| POST | /sessions/{code}/answers | Submit an answer | Player | 201 | 400, 401, 403, 404, 409 |
| POST | /sessions/{code}/chests | Open a mystery chest | Player | 201 | 400, 401, 403, 404, 409 |
| GET | /sessions/{code}/leaderboard | Ranking | No | 200 | 404 |

## Game rules (change them in app/rules.py)
- Correct answer: 10 stars. Streak of 3-4: x1.5. Streak of 5 or more: x2.
- Wrong answer or timeout: lose 1 life, lose 5 stars (not below 0), streak resets.
- Every 5th correct answer in a row: 3 chests (Double Star, Protection Card, Empty), shuffled.
  Pick one. Unopened chests expire after 30 seconds and block the next question until then.
- Double Star: next correct answer earns 2x stars.
- Protection Card: next wrong answer costs no stars and keeps the streak (the life is still lost).
- Out of lives: the player is finished. Session time runs out: the game ends.
- Rank: most stars, then most correct answers, then fastest average answer time.
- Start: 3 lives, 5 minutes, up to 30 players (host can change lives and time).

## Error codes
SESSION_NOT_FOUND, SESSION_ENDED, SESSION_NOT_STARTED, SESSION_FULL, NICKNAME_TAKEN,
NICKNAME_NOT_ALLOWED, QUESTION_SET_NOT_FOUND, NOT_YOUR_QUESTION_SET, NOT_YOUR_SESSION,
QUESTION_SET_IN_USE, QUESTION_NOT_ACTIVE, PLAYER_OUT_OF_LIVES, CHEST_PENDING,
CHEST_NOT_FOUND, CHEST_ALREADY_OPENED, CHEST_EXPIRED, WRONG_SESSION, plus the shared
AUTH_REQUIRED, INVALID_CREDENTIALS, VALIDATION_FAILED, FORBIDDEN, NOT_FOUND, SERVER_ERROR, DATABASE_DOWN.

## Folder map
    main.py            start here (py main.py)
    app/main.py        FastAPI app, CORS, routers
    app/routes/        one file per group of endpoints (controllers)
    app/services/      game rules and checks
    app/repositories/  all SQL lives here
    app/rules.py       numbers for stars, lives, chests
    docs/schema.sql    database tables
