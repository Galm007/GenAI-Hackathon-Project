from __future__ import annotations

from app.embeddings import embed_texts

from .common import PROCESSED_DIR, log, read_jsonl, supabase

UPSERT_BATCH = 500


async def load_twins() -> None:
    sb = await supabase()
    rows = list(read_jsonl(PROCESSED_DIR / "twins.jsonl"))
    rows = list({r["reddit_id"]: r for r in rows}.values())          # last write wins
    log.info("embedding %d profiles", len(rows))
    vectors = await embed_texts([r["profile_text"] for r in rows])
    for r, v in zip(rows, vectors, strict=True):
        r["embedding"] = v                                          # PostgREST casts JSON array → vector(768)
    for i in range(0, len(rows), UPSERT_BATCH):
        await sb.table("applicant_twins").upsert(rows[i : i + UPSERT_BATCH], on_conflict="reddit_id").execute()
        log.info("upserted %d/%d", min(i + UPSERT_BATCH, len(rows)), len(rows))


if __name__ == "__main__":
    import asyncio

    asyncio.run(load_twins())
