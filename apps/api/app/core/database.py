from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


database_url = _normalize_database_url(settings.database_url)
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}

engine = create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


RLS_STATEMENTS = (
    """
    alter table public.video_jobs enable row level security;
    """,
    """
    alter table public.video_jobs force row level security;
    """,
    """
    drop policy if exists "video_jobs_select_own" on public.video_jobs;
    """,
    """
    create policy "video_jobs_select_own" on public.video_jobs
    for select
    to authenticated
    using (user_id = (select auth.uid())::text);
    """,
    """
    drop policy if exists "video_jobs_insert_own" on public.video_jobs;
    """,
    """
    create policy "video_jobs_insert_own" on public.video_jobs
    for insert
    to authenticated
    with check (user_id = (select auth.uid())::text);
    """,
    """
    drop policy if exists "video_jobs_update_own" on public.video_jobs;
    """,
    """
    create policy "video_jobs_update_own" on public.video_jobs
    for update
    to authenticated
    using (user_id = (select auth.uid())::text)
    with check (user_id = (select auth.uid())::text);
    """,
    """
    drop policy if exists "video_jobs_delete_own" on public.video_jobs;
    """,
    """
    create policy "video_jobs_delete_own" on public.video_jobs
    for delete
    to authenticated
    using (user_id = (select auth.uid())::text);
    """,
    """
    alter table public.video_caption_results enable row level security;
    """,
    """
    alter table public.video_caption_results force row level security;
    """,
    """
    drop policy if exists "video_caption_results_select_own" on public.video_caption_results;
    """,
    """
    create policy "video_caption_results_select_own" on public.video_caption_results
    for select
    to authenticated
    using (
      exists (
        select 1
        from public.video_jobs
        where public.video_jobs.id = public.video_caption_results.job_id
          and public.video_jobs.user_id = (select auth.uid())::text
      )
    );
    """,
    """
    drop policy if exists "video_caption_results_insert_own" on public.video_caption_results;
    """,
    """
    create policy "video_caption_results_insert_own" on public.video_caption_results
    for insert
    to authenticated
    with check (
      exists (
        select 1
        from public.video_jobs
        where public.video_jobs.id = public.video_caption_results.job_id
          and public.video_jobs.user_id = (select auth.uid())::text
      )
    );
    """,
    """
    drop policy if exists "video_caption_results_update_own" on public.video_caption_results;
    """,
    """
    create policy "video_caption_results_update_own" on public.video_caption_results
    for update
    to authenticated
    using (
      exists (
        select 1
        from public.video_jobs
        where public.video_jobs.id = public.video_caption_results.job_id
          and public.video_jobs.user_id = (select auth.uid())::text
      )
    )
    with check (
      exists (
        select 1
        from public.video_jobs
        where public.video_jobs.id = public.video_caption_results.job_id
          and public.video_jobs.user_id = (select auth.uid())::text
      )
    );
    """,
    """
    drop policy if exists "video_caption_results_delete_own" on public.video_caption_results;
    """,
    """
    create policy "video_caption_results_delete_own" on public.video_caption_results
    for delete
    to authenticated
    using (
      exists (
        select 1
        from public.video_jobs
        where public.video_jobs.id = public.video_caption_results.job_id
          and public.video_jobs.user_id = (select auth.uid())::text
      )
    );
    """,
)


def _is_postgres() -> bool:
    return engine.dialect.name == "postgresql"


def apply_row_level_security() -> None:
    if not _is_postgres():
        return

    with engine.begin() as connection:
        for statement in RLS_STATEMENTS:
            connection.execute(text(statement))


def ensure_video_job_schema() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "video_jobs" not in table_names:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("video_jobs")}
    statements: list[str] = []

    if "processing_started_at" not in existing_columns:
        statements.append(
            "alter table public.video_jobs add column if not exists processing_started_at timestamptz"
            if _is_postgres()
            else "alter table video_jobs add column processing_started_at datetime"
        )
    if "preprocessing_metadata" not in existing_columns:
        statements.append(
            "alter table public.video_jobs add column if not exists preprocessing_metadata jsonb not null default '{}'::jsonb"
            if _is_postgres()
            else "alter table video_jobs add column preprocessing_metadata json not null default '{}'"
        )

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def ensure_storage_bucket_configuration() -> None:
    if not _is_postgres():
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
                values (
                  :bucket_id,
                  :bucket_name,
                  false,
                  52428800,
                  :allowed_mime_types
                )
                on conflict (id) do update
                set
                  public = excluded.public,
                  file_size_limit = excluded.file_size_limit,
                  allowed_mime_types = excluded.allowed_mime_types
                """
            ),
            {
                "bucket_id": settings.supabase_storage_bucket,
                "bucket_name": settings.supabase_storage_bucket,
                "allowed_mime_types": [
                    "video/mp4",
                    "video/quicktime",
                    "video/webm",
                    "video/x-matroska",
                    "audio/wav",
                    "audio/x-wav",
                    "application/octet-stream",
                ],
            },
        )


def initialize_database() -> None:
    from app.models.job import VideoCaptionResult, VideoJob

    Base.metadata.create_all(bind=engine)
    ensure_video_job_schema()
    ensure_storage_bucket_configuration()
    apply_row_level_security()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
