
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
from pathlib import Path

app = FastAPI(title="Snoooooze Readings")

BASE = Path(__file__).parent
DB = BASE / "snoooooze.db"

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def initialize():
    with connect() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            likes INTEGER DEFAULT 0
        )
        """)

        con.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY(article_id) REFERENCES articles(id)
        )
        """)

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
        return [dict(row) for row in rows]

@app.post("/api/articles")
def create_article(article: Article):
    with connect() as con:
        cursor = con.execute("""
            INSERT INTO articles (author, title, category, content)
            VALUES (?, ?, ?, ?)
        """, (
            article.author,
            article.title,
            article.category,
            article.content
        ))
        return {"message": "Published", "id": cursor.lastrowid}

@app.post("/api/articles/{article_id}/like")
def like_article(article_id: int):
    with connect() as con:
        result = con.execute(
            "UPDATE articles SET likes = likes + 1 WHERE id = ?",
            (article_id,)
        )
        if result.rowcount == 0:
            raise HTTPException(404, "Article not found")
        row = con.execute(
            "SELECT likes FROM articles WHERE id = ?",
            (article_id,)
        ).fetchone()
        return {"likes": row["likes"]}

@app.get("/api/articles/{article_id}/comments")
def get_comments(article_id: int):
    with connect() as con:
        return [
            dict(row) for row in con.execute(
                "SELECT * FROM comments WHERE article_id = ? ORDER BY id",
                (article_id,)
            ).fetchall()
        ]

@app.post("/api/articles/{article_id}/comments")
def add_comment(article_id: int, comment: Comment):
    with connect() as con:
        exists = con.execute(
            "SELECT id FROM articles WHERE id = ?",
            (article_id,)
        ).fetchone()

        if not exists:
            raise HTTPException(404, "Article not found")

        cursor = con.execute("""
            INSERT INTO comments (article_id, author, content)
            VALUES (?, ?, ?)
        """, (article_id, comment.author, comment.content))

        return {"message": "Comment added", "id": cursor.lastrowid}

app.mount(
    "/static",
    StaticFiles(directory=BASE / "static"),
    name="static"
)
