
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Snoooooze Readings")

BASE = Path(__file__).parent
DATABASE_URL = os.environ.get("DATABASE_URL")

def connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return psycopg.connect(url, row_factory=dict_row)


def initialize():
    with connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id BIGSERIAL PRIMARY KEY,
                author TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                likes INTEGER DEFAULT 0
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id BIGSERIAL PRIMARY KEY,
                article_id BIGINT NOT NULL REFERENCES articles(id)
                    ON DELETE CASCADE,
                author TEXT NOT NULL,
                content TEXT NOT NULL
            )
        """)


@app.on_event("startup")
def startup():
    initialize()


class Article(BaseModel):
    author: str
    title: str
    category: str
    content: str


class Comment(BaseModel):
    author: str
    content: str


@app.get("/")
def home():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/api/articles")
def get_articles():
    with connect() as con:
        rows = con.execute(
            "SELECT * FROM articles ORDER BY id DESC"
        ).fetchall()
        return rows


@app.post("/api/articles")
def create_article(article: Article):
    with connect() as con:
        row = con.execute("""
            INSERT INTO articles (author, title, category, content)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            article.author,
            article.title,
            article.category,
            article.content
        )).fetchone()

        return {"message": "Published", "id": row["id"]}


@app.post("/api/articles/{article_id}/like")
def like_article(article_id: int):
    with connect() as con:
        row = con.execute("""
            UPDATE articles
            SET likes = likes + 1
            WHERE id = %s
            RETURNING likes
        """, (article_id,)).fetchone()

        if not row:
            raise HTTPException(404, "Article not found")

        return {"likes": row["likes"]}


@app.get("/api/articles/{article_id}/comments")
def get_comments(article_id: int):
    with connect() as con:
        return con.execute("""
            SELECT * FROM comments
            WHERE article_id = %s
            ORDER BY id
        """, (article_id,)).fetchall()


@app.post("/api/articles/{article_id}/comments")
def add_comment(article_id: int, comment: Comment):
    with connect() as con:
        exists = con.execute(
            "SELECT id FROM articles WHERE id = %s",
            (article_id,)
        ).fetchone()

        if not exists:
            raise HTTPException(404, "Article not found")

        row = con.execute("""
            INSERT INTO comments (article_id, author, content)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (
            article_id,
            comment.author,
            comment.content
        )).fetchone()

        return {"message": "Comment added", "id": row["id"]}


app.mount(
    "/static",
    StaticFiles(directory=BASE / "static"),
    name="static"
)
