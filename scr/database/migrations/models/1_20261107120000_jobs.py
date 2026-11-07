from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "job_cooldown" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "job_key" VARCHAR(32) NOT NULL,
    "available_at" TIMESTAMP NOT NULL,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_job_cooldow_user_id_f0353a" UNIQUE ("user_id", "job_key")
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "job_cooldown";"""
