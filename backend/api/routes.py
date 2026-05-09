"""
API Routes - All endpoints for ArchIQ
"""
import uuid
import json
import asyncio
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import aiosqlite
import pdfplumber
import io

from db.database import get_db, DATABASE_URL
from ai_engine.engine import (
    extract_skills_from_text,
    compute_role_fit,
    compute_job_match,
    generate_gap_analysis,
    generate_mentor_response,
    generate_ai_explanation
)
from scraper.scraper import run_full_scrape

router = APIRouter()

# ── Pydantic models ────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: str

class SkillsInput(BaseModel):
    user_id: str
    text: str
    source_type: str = "manual"

class ChatMessage(BaseModel):
    user_id: str
    message: str

class JobSearchRequest(BaseModel):
    user_id: str
    query: Optional[str] = None
    force_refresh: bool = False

# ── Scrape state (simple in-memory for MVP) ────────────────────────────────────
scrape_state = {"status": "idle", "progress": 0, "message": "", "jobs_found": 0}

# ── User endpoints ─────────────────────────────────────────────────────────────

@router.post("/users")
async def create_user(user: UserCreate):
    user_id = str(uuid.uuid4())
    async with aiosqlite.connect(DATABASE_URL) as db:
        try:
            await db.execute(
                "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
                (user_id, user.name, user.email)
            )
            await db.commit()
        except Exception:
            # User exists - fetch them
            async with db.execute("SELECT id FROM users WHERE email = ?", (user.email,)) as cur:
                row = await cur.fetchone()
                if row:
                    user_id = row[0]
    return {"user_id": user_id, "name": user.name, "email": user.email}


@router.get("/users/{user_id}")
async def get_user(user_id: str):
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            return dict(row)


# ── Profile / Resume parsing ───────────────────────────────────────────────────

@router.post("/profile/upload")
async def upload_resume(user_id: str, file: UploadFile = File(...)):
    """Parse resume PDF or text and extract skills"""
    content = await file.read()

    # Extract text from PDF
    if file.filename and file.filename.lower().endswith(".pdf"):
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception:
            text = content.decode("utf-8", errors="ignore")
    else:
        text = content.decode("utf-8", errors="ignore")

    return await _process_skills(user_id, text, "resume_upload")


@router.post("/profile/text")
async def input_skills_text(data: SkillsInput):
    """Parse manually entered skills/description"""
    return await _process_skills(data.user_id, data.text, data.source_type)


async def _process_skills(user_id: str, text: str, source_type: str) -> dict:
    profile_id = str(uuid.uuid4())

    async with aiosqlite.connect(DATABASE_URL) as db:
        # Save profile
        await db.execute(
            "INSERT INTO profiles (id, user_id, raw_text, source_type) VALUES (?, ?, ?, ?)",
            (profile_id, user_id, text[:10000], source_type)
        )

        # Extract skills
        skills = extract_skills_from_text(text)

        # Delete old skills for user
        await db.execute("DELETE FROM user_skills WHERE user_id = ?", (user_id,))

        # Insert new skills
        for skill in skills:
            skill_id = str(uuid.uuid4())
            await db.execute(
                """INSERT INTO user_skills
                   (id, user_id, skill_name, depth_level, evidence_text, confidence, domain_cluster)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (skill_id, user_id, skill["skill_name"], skill["depth_level"],
                 skill["evidence_text"], skill["confidence"], skill["domain_cluster"])
            )

        await db.commit()

    return {
        "profile_id": profile_id,
        "skills_extracted": len(skills),
        "skills": skills,
        "message": f"Extracted {len(skills)} technical skills from your profile"
    }


# ── Skill & Role endpoints ─────────────────────────────────────────────────────

@router.get("/skills/{user_id}")
async def get_user_skills(user_id: str):
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_skills WHERE user_id = ? ORDER BY confidence DESC",
            (user_id,)
        ) as cur:
            rows = await cur.fetchall()
            return {"skills": [dict(r) for r in rows]}


@router.get("/role-fit/{user_id}")
async def get_role_fit(user_id: str):
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT skill_name, depth_level, evidence_text, confidence, domain_cluster FROM user_skills WHERE user_id = ?",
            (user_id,)
        ) as cur:
            rows = await cur.fetchall()
            user_skills = [dict(r) for r in rows]

    # Map skill names to IDs for ontology matching
    from ai_engine.ontology import DOMAIN_ONTOLOGY, SKILL_ALIASES
    skill_id_map = {}
    for skill_id, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            skill_id_map[alias.lower()] = skill_id

    enriched_skills = []
    for s in user_skills:
        name_lower = s["skill_name"].lower()
        # Try to find skill_id
        sid = None
        for alias, skill_id in skill_id_map.items():
            if alias in name_lower or name_lower in alias:
                sid = skill_id
                break
        if sid:
            s["skill_id"] = sid
            enriched_skills.append(s)

    role_fits = compute_role_fit(enriched_skills)
    return {"role_fits": role_fits, "total_skills": len(user_skills)}


@router.get("/gap-analysis/{user_id}")
async def get_gap_analysis(user_id: str):
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT skill_name, depth_level, domain_cluster FROM user_skills WHERE user_id = ?",
            (user_id,)
        ) as cur:
            rows = await cur.fetchall()
            user_skills = [dict(r) for r in rows]

    # Get role fits first
    from ai_engine.ontology import SKILL_ALIASES
    skill_id_map = {}
    for skill_id, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            skill_id_map[alias.lower()] = skill_id

    enriched = []
    for s in user_skills:
        name_lower = s["skill_name"].lower()
        for alias, skill_id in skill_id_map.items():
            if alias in name_lower or name_lower in alias:
                s["skill_id"] = skill_id
                enriched.append(s)
                break

    role_fits = compute_role_fit(enriched)
    gaps = generate_gap_analysis(enriched, role_fits)
    return {"gaps": gaps}


# ── Job endpoints ──────────────────────────────────────────────────────────────

@router.get("/scrape/status")
async def get_scrape_status():
    return scrape_state


@router.post("/jobs/scrape")
async def trigger_scrape(request: JobSearchRequest, background_tasks: BackgroundTasks):
    """Trigger background job scraping"""
    if scrape_state["status"] == "running":
        return {"message": "Scrape already running", "status": scrape_state}

    scrape_state.update({"status": "running", "progress": 0, "message": "Starting...", "jobs_found": 0})

    async def do_scrape():
        async def progress_cb(msg, pct):
            scrape_state["message"] = msg
            scrape_state["progress"] = pct

        try:
            jobs = await run_full_scrape(request.query, progress_cb)

            async with aiosqlite.connect(DATABASE_URL) as db:
                new_count = 0
                for job in jobs:
                    try:
                        await db.execute(
                            """INSERT OR IGNORE INTO jobs
                               (id, title, company, location, job_type, source_url, jd_text, skills_json, fetched_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (job["id"], job["title"], job["company"], job["location"],
                             job.get("job_type", "full-time"), job.get("source_url", ""),
                             job.get("jd_text", ""), job.get("skills_json", "[]"),
                             job.get("fetched_at", datetime.utcnow().isoformat()))
                        )
                        new_count += 1
                    except Exception:
                        pass
                await db.commit()

            scrape_state.update({
                "status": "done",
                "progress": 100,
                "message": f"Found {new_count} jobs",
                "jobs_found": new_count
            })

        except Exception as e:
            scrape_state.update({"status": "error", "message": str(e), "progress": 0})

    # Use asyncio.create_task for true async background execution
    asyncio.create_task(do_scrape())
    return {"message": "Scrape started", "status": "running"}


@router.get("/jobs")
async def get_jobs(
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    min_score: int = 0
):
    """Get jobs, optionally matched to a user"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row

        if user_id:
            # Get matched jobs
            async with db.execute(
                """SELECT j.*, m.total_score, m.tech_score, m.arch_score, m.explanation_json
                   FROM jobs j
                   LEFT JOIN matches m ON j.id = m.job_id AND m.user_id = ?
                   WHERE j.is_active = 1
                   ORDER BY COALESCE(m.total_score, 0) DESC
                   LIMIT ? OFFSET ?""",
                (user_id, limit, offset)
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM jobs WHERE is_active = 1 ORDER BY fetched_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ) as cur:
                rows = await cur.fetchall()

        jobs = []
        for row in rows:
            j = dict(row)
            # Parse skills JSON
            try:
                j["skills_list"] = json.loads(j.get("skills_json", "[]"))
            except Exception:
                j["skills_list"] = []
            jobs.append(j)

        async with db.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1") as cur:
            total = (await cur.fetchone())[0]

    return {"jobs": jobs, "total": total, "offset": offset, "limit": limit}


@router.post("/jobs/match/{user_id}")
async def compute_matches(user_id: str, background_tasks: BackgroundTasks):
    """Compute match scores for all jobs for a user"""
    async def do_match():
        async with aiosqlite.connect(DATABASE_URL) as db:
            db.row_factory = aiosqlite.Row

            # Get user skills
            async with db.execute(
                "SELECT * FROM user_skills WHERE user_id = ?", (user_id,)
            ) as cur:
                user_skills = [dict(r) for r in await cur.fetchall()]

            from ai_engine.ontology import SKILL_ALIASES
            skill_id_map = {}
            for skill_id, aliases in SKILL_ALIASES.items():
                for alias in aliases:
                    skill_id_map[alias.lower()] = skill_id

            enriched = []
            for s in user_skills:
                name_lower = s["skill_name"].lower()
                for alias, skill_id in skill_id_map.items():
                    if alias in name_lower or name_lower in alias:
                        s["skill_id"] = skill_id
                        enriched.append(s)
                        break

            # Get all jobs
            async with db.execute("SELECT * FROM jobs WHERE is_active = 1") as cur:
                jobs = [dict(r) for r in await cur.fetchall()]

            # Compute matches
            for job in jobs:
                match = compute_job_match(enriched, job)
                match_id = str(uuid.uuid4())
                try:
                    await db.execute(
                        """INSERT OR REPLACE INTO matches
                           (id, user_id, job_id, total_score, tech_score, arch_score, explanation_json)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (match_id, user_id, job["id"], match["total_score"],
                         match["tech_score"], match.get("arch_score", 0),
                         json.dumps(match))
                    )
                except Exception:
                    pass

            await db.commit()

    asyncio.create_task(do_match())
    return {"message": "Match computation started"}


@router.get("/jobs/{job_id}/explain/{user_id}")
async def explain_job_match(job_id: str, user_id: str):
    """Get AI explanation for why a job matches"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)) as cur:
            job = dict(await cur.fetchone() or {})

        async with db.execute("SELECT * FROM user_skills WHERE user_id = ?", (user_id,)) as cur:
            user_skills = [dict(r) for r in await cur.fetchall()]

        async with db.execute(
            "SELECT * FROM matches WHERE job_id = ? AND user_id = ?", (job_id, user_id)
        ) as cur:
            match = dict(await cur.fetchone() or {})

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        match_data = json.loads(match.get("explanation_json", "{}"))
    except Exception:
        match_data = {}

    explanation = generate_ai_explanation(
        user_skills,
        job.get("title", ""),
        job.get("company", ""),
        match.get("total_score", 0),
        match_data.get("matching_skills", []),
        match_data.get("missing_skills", [])
    )

    return {"explanation": explanation, "job": job, "match": match}


# ── AI Mentor ─────────────────────────────────────────────────────────────────

@router.post("/mentor/chat")
async def mentor_chat(data: ChatMessage):
    """Chat with AI career mentor"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row

        # Get user skills
        async with db.execute(
            "SELECT * FROM user_skills WHERE user_id = ?", (data.user_id,)
        ) as cur:
            user_skills = [dict(r) for r in await cur.fetchall()]

        # Get conversation history
        async with db.execute(
            "SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 8",
            (data.user_id,)
        ) as cur:
            history = [dict(r) for r in await cur.fetchall()]
            history.reverse()

        # Save user message
        await db.execute(
            "INSERT INTO chat_messages (id, user_id, role, content) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), data.user_id, "user", data.message)
        )
        await db.commit()

    # Get role fits for context
    from ai_engine.ontology import SKILL_ALIASES
    skill_id_map = {}
    for skill_id, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            skill_id_map[alias.lower()] = skill_id
    enriched = []
    for s in user_skills:
        name_lower = s["skill_name"].lower()
        for alias, skill_id in skill_id_map.items():
            if alias in name_lower or name_lower in alias:
                s["skill_id"] = skill_id
                enriched.append(s)
                break

    role_fits = compute_role_fit(enriched)

    response = await generate_mentor_response(data.message, enriched, role_fits, history)

    # Save response
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT INTO chat_messages (id, user_id, role, content) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), data.user_id, "assistant", response)
        )
        await db.commit()

    return {"response": response, "role": "assistant"}


@router.get("/mentor/history/{user_id}")
async def get_chat_history(user_id: str, limit: int = 20):
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT role, content, created_at FROM chat_messages WHERE user_id = ? ORDER BY created_at ASC LIMIT ?",
            (user_id, limit)
        ) as cur:
            rows = await cur.fetchall()
    return {"messages": [dict(r) for r in rows]}


# ── Dashboard summary ──────────────────────────────────────────────────────────

@router.get("/dashboard/{user_id}")
async def get_dashboard(user_id: str):
    """Full dashboard data for a user"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute(
            "SELECT * FROM user_skills WHERE user_id = ? ORDER BY confidence DESC",
            (user_id,)
        ) as cur:
            user_skills = [dict(r) for r in await cur.fetchall()]

        async with db.execute(
            """SELECT j.title, j.company, j.location, j.source_url, j.skills_json, j.job_type,
                      m.total_score, m.tech_score, m.arch_score
               FROM matches m JOIN jobs j ON m.job_id = j.id
               WHERE m.user_id = ?
               ORDER BY m.total_score DESC LIMIT 10""",
            (user_id,)
        ) as cur:
            top_matches = [dict(r) for r in await cur.fetchall()]

        async with db.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1") as cur:
            total_jobs = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM matches WHERE user_id = ? AND total_score >= 70", (user_id,)
        ) as cur:
            strong_matches = (await cur.fetchone())[0]

    from ai_engine.ontology import SKILL_ALIASES
    skill_id_map = {}
    for skill_id, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            skill_id_map[alias.lower()] = skill_id
    enriched = []
    for s in user_skills:
        name_lower = s["skill_name"].lower()
        for alias, skill_id in skill_id_map.items():
            if alias in name_lower or name_lower in alias:
                s["skill_id"] = skill_id
                enriched.append(s)
                break

    role_fits = compute_role_fit(enriched)
    gaps = generate_gap_analysis(enriched, role_fits)

    arch_score = round(
        sum(1 for s in user_skills if s.get("depth_level") in ["architecture_reasoning", "production_exposure"]) /
        max(len(user_skills), 1) * 100 + 40
    )

    return {
        "user_skills": user_skills,
        "role_fits": role_fits[:8],
        "top_matches": top_matches,
        "gaps": gaps[:5],
        "stats": {
            "total_skills": len(user_skills),
            "total_jobs": total_jobs,
            "strong_matches": strong_matches,
            "arch_score": min(99, arch_score),
            "skill_depth_score": round(
                sum({"awareness": 1, "implementation": 2, "optimization": 3,
                     "architecture_reasoning": 4, "production_exposure": 5}.get(
                    s.get("depth_level", "awareness"), 1) for s in user_skills) /
                max(len(user_skills), 1) * 20
            )
        }
    }
