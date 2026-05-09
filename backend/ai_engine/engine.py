"""
AI Engine - Free, no API keys required
Uses:
- sentence-transformers (local, free) for embeddings + semantic similarity
- HuggingFace inference API (free tier) for text classification
- Rule-based + regex for skill extraction (fast, reliable)
- Cosine similarity for job matching
"""
import re
import json
import asyncio
import httpx
from typing import List, Dict, Tuple, Optional
from ai_engine.ontology import DOMAIN_ONTOLOGY

# ── Depth estimation rules (no LLM needed, pattern matching is reliable) ──────
DEPTH_PATTERNS = {
    "production_exposure": [
        r"production", r"deployed", r"tape.?out", r"silicon", r"bring.?up",
        r"shipped", r"manufacturing", r"validated at", r"real chip", r"customer"
    ],
    "architecture_reasoning": [
        r"design(ed)?", r"architect(ed)?", r"tradeoff", r"analysis of",
        r"sensitivity analysis", r"evaluated", r"compared", r"micro.?arch",
        r"reasoning", r"proposed", r"designed the", r"authored"
    ],
    "optimization": [
        r"optim", r"tuned", r"improved by", r"reduced", r"increased.*%",
        r"profil(ed|ing)", r"bottleneck", r"throughput", r"latency reduction",
        r"workload.*analysis", r"performance.*engineer"
    ],
    "implementation": [
        r"implement(ed)?", r"develop(ed)?", r"wrote", r"built", r"coded",
        r"program(med)?", r"creat(ed)?", r"constructed", r"verified"
    ],
    "awareness": [
        r"familiar", r"knowledge of", r"understand", r"studied", r"aware",
        r"learned", r"coursework", r"exposure to", r"basic"
    ]
}

SKILL_ALIASES = {
    # PMU / Performance
    "pmu": ["pmu", "performance monitoring unit", "performance counter", "hardware counter",
            "perf counter", "cycle counter", "instruction counter", "arm pmu"],
    "workload_profiling": ["workload profil", "profil", "vtune", "perf tool", "gprof",
                           "hotspot analysis", "flame graph", "sampling"],
    "benchmarking": ["benchmark", "spec cpu", "coremark", "dhrystone", "microbenchmark",
                     "throughput test", "latency test", "performance test"],
    "cache_analysis": ["cache analysis", "cache sensitivity", "cache miss", "cache hit",
                       "cache behavior", "memory footprint", "working set"],
    "ipc_analysis": ["ipc", "cpi", "instructions per cycle", "cycles per instruction",
                     "roofline", "execution unit"],

    # Arch validation
    "bist": ["bist", "built-in self test", "self test", "memory bist", "logic bist"],
    "scan_chain": ["scan chain", "scan test", "shift register", "scan design"],
    "dft": ["dft", "design for test", "design for testability", "testability"],
    "atpg": ["atpg", "automatic test pattern", "test pattern generation"],
    "jtag": ["jtag", "boundary scan", "ieee 1149", "debug interface"],
    "post_silicon_validation": ["post-silicon", "post silicon", "silicon validation",
                                "chip validation", "hardware validation", "silicon debug"],
    "silicon_bringup": ["bring-up", "bringup", "bring up", "silicon bring"],

    # SoC / Embedded
    "amba_apb": ["amba apb", "apb protocol", "apb bus", "advanced peripheral bus"],
    "amba_axi": ["amba axi", "axi protocol", "axi bus", "advanced extensible interface",
                 "axi4", "axi lite"],
    "amba_ahb": ["amba ahb", "ahb protocol", "ahb bus"],
    "rtos": ["rtos", "real-time os", "freertos", "vxworks", "zephyr", "threadx",
             "real time operating", "preemptive"],
    "bare_metal": ["bare metal", "baremetal", "no os", "without os", "embedded c",
                   "embedded firmware", "microcontroller"],
    "linker_scripts": ["linker script", "linker file", "ld script", "memory map",
                       "scatter file", "memory layout", "link time"],
    "mpu": ["mpu", "memory protection unit", "memory protection"],
    "mmu": ["mmu", "memory management unit", "virtual memory", "page table", "tlb"],
    "interrupt_handling": ["interrupt", "isr", "irq", "exception handler", "nvic"],
    "dma": ["dma", "direct memory access", "memory transfer", "dma controller"],

    # Computer Architecture
    "ooo_execution": ["out-of-order", "ooo", "o3", "reorder buffer", "rob",
                      "reservation station", "tomasulo", "register renaming"],
    "branch_prediction": ["branch predict", "btb", "ras", "gshare", "misprediction",
                          "branch target"],
    "cache_hierarchy": ["cache hierarchy", "l1 cache", "l2 cache", "l3 cache",
                        "cache line", "cache set", "associativity", "eviction"],
    "simd": ["simd", "vector processing", "sse", "avx", "neon", "sve", "vectoriz"],
    "simt": ["simt", "warp", "thread block", "gpu thread", "single instruction multiple thread"],
    "risc_v": ["risc-v", "riscv", "risc v"],
    "noc": ["noc", "network on chip", "on-chip network", "mesh network", "crossbar"],
    "pipeline_design": ["pipeline", "5-stage", "fetch decode execute", "hazard",
                        "forwarding", "stall", "flush"],

    # AI Accelerators
    "systolic_array": ["systolic array", "systolic", "matrix multiply unit", "mxu", "tpu"],
    "tensor_core": ["tensor core", "matrix core", "wmma", "cublas", "tensor operation"],
    "cuda": ["cuda", "cuDNN", "cuda kernel", "gpu programming", "parallel programming"],
    "dataflow_architecture": ["dataflow", "spatial architecture", "eyeriss", "dataflow schedule"],
    "quantization": ["quantization", "int8", "fp16", "bf16", "mixed precision", "post-training quant"],
    "mlir": ["mlir", "mlir dialect", "multi-level ir"],

    # HW/SW
    "device_drivers": ["device driver", "kernel driver", "linux driver", "driver develop"],
    "cache_coherence": ["cache coherence", "mesi", "moesi", "coherence protocol", "snoop"],
    "memory_consistency": ["memory consistency", "memory ordering", "tso", "weak ordering",
                           "memory model", "acquire release", "memory barrier"],
    "firmware": ["firmware", "embedded firmware", "firmware develop"],
    "hw_sw_interface": ["hw/sw interface", "hardware software interface", "hardware abstraction",
                        "hal", "bsp", "board support"],

    # Compiler
    "llvm": ["llvm", "clang", "llvm ir", "llvm pass", "middle end"],
    "gcc": ["gcc", "gnu compiler", "g++"],
    "vectorization": ["auto-vectoriz", "loop vectoriz", "simd vectoriz"],
    "jit": ["jit", "just-in-time", "dynamic compilation"],
}


def extract_skills_from_text(text: str) -> List[Dict]:
    """
    Extract skills from resume/profile text using alias matching + context window
    Returns list of {skill_id, skill_name, evidence_text, depth_level, confidence}
    """
    text_lower = text.lower()
    found_skills = []
    seen_skills = set()

    sentences = re.split(r'[.!?\n]+', text)

    for skill_id, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            pattern = re.compile(r'\b' + re.escape(alias.lower()) + r'\b', re.IGNORECASE)
            if pattern.search(text_lower):
                if skill_id in seen_skills:
                    continue
                seen_skills.add(skill_id)

                # Find best evidence sentence
                evidence = ""
                best_depth = "awareness"
                best_score = 0

                for sentence in sentences:
                    if pattern.search(sentence.lower()):
                        depth, score = estimate_depth(sentence)
                        if score > best_score:
                            best_score = score
                            best_depth = depth
                            evidence = sentence.strip()

                skill_info = DOMAIN_ONTOLOGY["skills"].get(skill_id, {})
                domain = skill_info.get("domain", "general")
                confidence = min(0.95, 0.6 + (best_score * 0.1))

                found_skills.append({
                    "skill_id": skill_id,
                    "skill_name": skill_info.get("name", skill_id.replace("_", " ").title()),
                    "domain_cluster": domain,
                    "evidence_text": evidence[:300],
                    "depth_level": best_depth,
                    "confidence": round(confidence, 2)
                })
                break

    return found_skills


def estimate_depth(sentence: str) -> Tuple[str, int]:
    """
    Estimate skill depth from context sentence
    Returns (depth_level, score)
    """
    sentence_lower = sentence.lower()

    for depth in ["production_exposure", "architecture_reasoning", "optimization",
                  "implementation", "awareness"]:
        patterns = DEPTH_PATTERNS[depth]
        matches = sum(1 for p in patterns if re.search(p, sentence_lower))
        if matches > 0:
            score = {"production_exposure": 5, "architecture_reasoning": 4,
                     "optimization": 3, "implementation": 2, "awareness": 1}[depth]
            return depth, score

    return "implementation", 2  # default


def compute_role_fit(user_skills: List[Dict]) -> List[Dict]:
    """
    Score user against each role in the ontology
    Returns list of {role_id, role_label, score, matching_skills, missing_skills}
    """
    user_skill_ids = {s["skill_id"] for s in user_skills}
    user_depth_map = {s["skill_id"]: s["depth_level"] for s in user_skills}

    depth_scores = {
        "awareness": 0.4,
        "implementation": 0.65,
        "optimization": 0.80,
        "architecture_reasoning": 0.92,
        "production_exposure": 1.0
    }

    results = []
    for role_id, role in DOMAIN_ONTOLOGY["roles"].items():
        primary = role["primary_skills"]
        secondary = role.get("secondary_skills", [])

        primary_score = 0
        for skill in primary:
            if skill in user_skill_ids:
                depth = user_depth_map.get(skill, "awareness")
                primary_score += depth_scores[depth]
        primary_pct = primary_score / len(primary) if primary else 0

        secondary_score = 0
        for skill in secondary:
            if skill in user_skill_ids:
                depth = user_depth_map.get(skill, "awareness")
                secondary_score += depth_scores[depth] * 0.5
        secondary_pct = secondary_score / len(secondary) if secondary else 0

        total = round((primary_pct * 0.7 + secondary_pct * 0.3) * 100)

        matching = [s for s in primary + secondary if s in user_skill_ids]
        missing = [s for s in primary if s not in user_skill_ids]

        results.append({
            "role_id": role_id,
            "role_label": role["label"],
            "score": total,
            "matching_skills": matching,
            "missing_skills": missing,
            "companies": role.get("companies", [])
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)


def compute_job_match(user_skills: List[Dict], job: Dict) -> Dict:
    """
    Score a single job against user profile
    Uses skill overlap + domain alignment
    """
    user_skill_ids = {s["skill_id"] for s in user_skills}
    user_depth_map = {s["skill_id"]: s["depth_level"] for s in user_skills}

    job_skills = json.loads(job.get("skills_json", "[]")) if isinstance(job.get("skills_json"), str) else job.get("skills_json", [])
    job_skill_ids = set(job_skills)

    depth_scores = {
        "awareness": 0.4, "implementation": 0.65, "optimization": 0.80,
        "architecture_reasoning": 0.92, "production_exposure": 1.0
    }

    if not job_skill_ids:
        return {"total_score": 30, "tech_score": 30, "arch_score": 30, "explanation": "Insufficient job data"}

    overlap = user_skill_ids & job_skill_ids
    tech_score = 0
    for skill_id in overlap:
        depth = user_depth_map.get(skill_id, "awareness")
        weight = DOMAIN_ONTOLOGY["skills"].get(skill_id, {}).get("weight", 0.5)
        tech_score += depth_scores[depth] * weight

    max_possible = sum(DOMAIN_ONTOLOGY["skills"].get(s, {}).get("weight", 0.5) for s in job_skill_ids)
    tech_pct = round((tech_score / max_possible * 100) if max_possible > 0 else 0)

    # Arch relevance: check if job skills are in architecture domains
    arch_domains = {"performance_engineering", "architecture_validation", "computer_architecture"}
    arch_job_skills = [s for s in job_skill_ids if
                       DOMAIN_ONTOLOGY["skills"].get(s, {}).get("domain") in arch_domains]
    arch_user_match = [s for s in arch_job_skills if s in user_skill_ids]
    arch_score = round((len(arch_user_match) / len(arch_job_skills) * 100) if arch_job_skills else 50)

    total = round(tech_pct * 0.6 + arch_score * 0.4)
    total = min(99, max(5, total))

    return {
        "total_score": total,
        "tech_score": min(99, tech_pct),
        "arch_score": min(99, arch_score),
        "matching_skills": list(overlap),
        "missing_skills": list(job_skill_ids - user_skill_ids),
        "explanation": f"Matched {len(overlap)}/{len(job_skill_ids)} required skills. Architecture relevance: {arch_score}%."
    }


def generate_gap_analysis(user_skills: List[Dict], role_fits: List[Dict]) -> List[Dict]:
    """
    Generate prioritized gap analysis based on role fits and missing skills
    """
    user_skill_ids = {s["skill_id"] for s in user_skills}
    gap_counts = {}

    for role in role_fits[:5]:  # top 5 target roles
        for missing_skill in role["missing_skills"]:
            if missing_skill not in gap_counts:
                gap_counts[missing_skill] = {"count": 0, "roles": []}
            gap_counts[missing_skill]["count"] += 1
            gap_counts[missing_skill]["roles"].append(role["role_label"])

    gaps = []
    for skill_id, info in gap_counts.items():
        skill_meta = DOMAIN_ONTOLOGY["skills"].get(skill_id, {})
        priority = "high" if info["count"] >= 3 else ("medium" if info["count"] >= 2 else "low")

        gaps.append({
            "skill_id": skill_id,
            "skill_name": skill_meta.get("name", skill_id.replace("_", " ").title()),
            "priority": priority,
            "reason_text": f"Required by {info['count']} of your top target roles: {', '.join(info['roles'][:3])}",
            "domain": skill_meta.get("domain", "general"),
            "count": info["count"]
        })

    return sorted(gaps, key=lambda x: x["count"], reverse=True)


def generate_ai_explanation(
    user_skills: List[Dict],
    job_title: str,
    company: str,
    match_score: int,
    matching_skills: List[str],
    missing_skills: List[str]
) -> str:
    """
    Generate human-readable explanation (rule-based, no LLM needed)
    """
    skill_names = {k: v["name"] for k, v in DOMAIN_ONTOLOGY["skills"].items()}

    matching_names = [skill_names.get(s, s.replace("_", " ").title()) for s in matching_skills[:4]]
    missing_names = [skill_names.get(s, s.replace("_", " ").title()) for s in missing_skills[:3]]

    depth_map = {s["skill_id"]: s["depth_level"] for s in user_skills}
    strong = [s for s in matching_skills if depth_map.get(s) in ["architecture_reasoning", "production_exposure"]]
    strong_names = [skill_names.get(s, s) for s in strong[:2]]

    explanation = f"You match **{match_score}%** for the {job_title} role at {company}. "

    if strong_names:
        explanation += f"Your deep expertise in {', '.join(strong_names)} is a strong differentiator. "

    if matching_names:
        explanation += f"You already have {len(matching_skills)} required skills including {', '.join(matching_names[:3])}. "

    if missing_names:
        explanation += f"To reach 95%+ match, focus on gaining depth in: {', '.join(missing_names)}."
    else:
        explanation += "Your profile is well-aligned — apply with confidence."

    return explanation


async def generate_mentor_response(
    question: str,
    user_skills: List[Dict],
    role_fits: List[Dict],
    conversation_history: List[Dict]
) -> str:
    """
    AI mentor response using HuggingFace Inference API (free)
    Falls back to rule-based if API unavailable
    """
    try:
        context = build_mentor_context(user_skills, role_fits)
        prompt = f"""You are ArchIQ, an expert career mentor for hardware and embedded systems engineers.
You specialize in computer architecture, SoC design, performance engineering, and AI accelerators.

User profile context:
{context}

Conversation history:
{chr(10).join([f"{m['role']}: {m['content']}" for m in conversation_history[-4:]])}

User question: {question}

Give a specific, technical, and actionable answer. Reference their actual skills and gaps. Be concise (3-5 sentences max)."""

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
                headers={"Content-Type": "application/json"},
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 300,
                        "temperature": 0.7,
                        "return_full_text": False
                    }
                }
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data:
                    return data[0].get("generated_text", "").strip()
    except Exception:
        pass

    return rule_based_mentor(question, user_skills, role_fits)


def build_mentor_context(user_skills: List[Dict], role_fits: List[Dict]) -> str:
    top_skills = [f"{s['skill_name']} ({s['depth_level']})" for s in user_skills[:6]]
    top_roles = [f"{r['role_label']} ({r['score']}%)" for r in role_fits[:3]]
    return f"Skills: {', '.join(top_skills)}\nTop role fits: {', '.join(top_roles)}"


def rule_based_mentor(question: str, user_skills: List[Dict], role_fits: List[Dict]) -> str:
    q = question.lower()
    top_role = role_fits[0] if role_fits else None
    skill_names = [s["skill_name"] for s in user_skills[:3]]

    if any(w in q for w in ["why", "match", "fit", "suited"]):
        if top_role:
            return (f"Your strongest fit is **{top_role['role_label']}** at {top_role['score']}% match. "
                    f"This is driven by your expertise in {', '.join(skill_names)}. "
                    f"These skills map directly to the core requirements for this role.")

    if any(w in q for w in ["gap", "missing", "learn", "improve", "skill"]):
        missing = role_fits[0]["missing_skills"][:2] if role_fits else []
        names = [DOMAIN_ONTOLOGY["skills"].get(s, {}).get("name", s) for s in missing]
        return (f"Your highest-leverage gaps are: {', '.join(names)}. "
                f"For GPU/accelerator roles, I recommend starting with CUDA programming fundamentals, "
                f"then diving into the memory hierarchy and warp execution model. "
                f"For arch validation roles, strengthen your BIST and scan chain depth.")

    if any(w in q for w in ["company", "nvidia", "intel", "arm", "tenstorrent"]):
        return ("Tenstorrent and Arm are excellent targets for your profile — both actively hire for "
                "architecture validation and performance engineering. Tenstorrent is particularly "
                "open to strong embedded/SoC backgrounds transitioning to AI hardware. "
                "Intel's architecture group in Bangalore is also a strong match.")

    if any(w in q for w in ["project", "build", "portfolio"]):
        return ("Build a cycle-accurate PMU event logger for a RISC-V core on an FPGA — this demonstrates "
                "performance engineering, embedded systems, and architecture knowledge simultaneously. "
                "Pair it with a roofline model analysis of a benchmark workload. "
                "This kind of end-to-end project is exactly what arch validation teams look for.")

    return (f"Based on your profile with expertise in {', '.join(skill_names)}, "
            f"I recommend focusing on deepening your architecture reasoning depth. "
            f"Your strongest career path leads toward {top_role['role_label'] if top_role else 'performance engineering'} roles. "
            f"What specific aspect would you like to explore further?")
