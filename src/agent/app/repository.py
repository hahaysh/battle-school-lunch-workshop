import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterator

from .schemas import AnalysisResult


class AnalysisRepository:
    def __init__(self, database_path: str):
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_date TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    winner TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    quality_gate_passed INTEGER NOT NULL,
                    quality_gate_warnings TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS schools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    office_code TEXT NOT NULL,
                    school_code TEXT NOT NULL,
                    school_name TEXT NOT NULL,
                    UNIQUE(office_code, school_code)
                );
                CREATE TABLE IF NOT EXISTS analysis_schools (
                    analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
                    school_id INTEGER NOT NULL REFERENCES schools(id),
                    PRIMARY KEY (analysis_id, school_id)
                );
                CREATE TABLE IF NOT EXISTS agent_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
                    school_id INTEGER NOT NULL REFERENCES schools(id),
                    area_key TEXT NOT NULL,
                    area_name TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    weight INTEGER NOT NULL,
                    evidence TEXT NOT NULL
                );
                """
            )

    def save(self, analysis_date: date, prompt: str, result: AnalysisResult) -> int:
        with self._connection() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO analyses
                        (analysis_date, prompt, winner, summary, quality_gate_passed, quality_gate_warnings, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        analysis_date.isoformat(),
                        prompt,
                        result.winner,
                        result.summary,
                        int(result.qualityGate.passed),
                        "\n".join(result.qualityGate.warnings),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                analysis_id = cursor.lastrowid
                if analysis_id is None:
                    raise RuntimeError("분석 ID를 생성하지 못했습니다.")
                for school_result in result.schools:
                    school = school_result.school
                    school_cursor = connection.execute(
                        """
                        INSERT INTO schools (office_code, school_code, school_name)
                        VALUES (?, ?, ?)
                        ON CONFLICT(office_code, school_code) DO UPDATE SET school_name=excluded.school_name
                        """,
                        (school["officeCode"], school["schoolCode"], school["schoolName"]),
                    )
                    school_id = school_cursor.lastrowid
                    if not school_id:
                        school_id = connection.execute(
                            "SELECT id FROM schools WHERE office_code = ? AND school_code = ?",
                            (school["officeCode"], school["schoolCode"]),
                        ).fetchone()["id"]
                    connection.execute(
                        "INSERT INTO analysis_schools (analysis_id, school_id) VALUES (?, ?)",
                        (analysis_id, school_id),
                    )
                    for area in school_result.areas:
                        connection.execute(
                            """
                            INSERT INTO agent_results
                                (analysis_id, school_id, area_key, area_name, score, weight, evidence)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                analysis_id,
                                school_id,
                                area.key,
                                area.name,
                                area.score,
                                area.weight,
                                "\n".join(area.evidence),
                            ),
                        )
                connection.commit()
                return int(analysis_id)
            except Exception:
                connection.rollback()
                raise

    def get(self, analysis_id: int) -> dict | None:
        with self._connection() as connection:
            analysis = connection.execute(
                "SELECT * FROM analyses WHERE id = ?", (analysis_id,)
            ).fetchone()
            if analysis is None:
                return None
            schools = connection.execute(
                """
                SELECT s.*, ar.total_score
                FROM analysis_schools link
                JOIN schools s ON s.id = link.school_id
                LEFT JOIN (
                    SELECT school_id, analysis_id, SUM(score * weight) / 5.0 AS total_score
                    FROM agent_results GROUP BY school_id, analysis_id
                ) ar ON ar.school_id = s.id AND ar.analysis_id = link.analysis_id
                WHERE link.analysis_id = ? ORDER BY s.id
                """,
                (analysis_id,),
            ).fetchall()
            school_results = []
            for school in schools:
                areas = connection.execute(
                    """
                    SELECT area_key, area_name, score, weight, evidence
                    FROM agent_results WHERE analysis_id = ? AND school_id = ? ORDER BY id
                    """,
                    (analysis_id, school["id"]),
                ).fetchall()
                school_results.append(
                    {
                        "school": {
                            "officeCode": school["office_code"],
                            "schoolCode": school["school_code"],
                            "schoolName": school["school_name"],
                        },
                        "totalScore": school["total_score"],
                        "areas": [
                            {
                                "key": area["area_key"],
                                "name": area["area_name"],
                                "score": area["score"],
                                "weight": area["weight"],
                                "evidence": area["evidence"].split("\n") if area["evidence"] else [],
                            }
                            for area in areas
                        ],
                    }
                )
            return {
                "analysisId": analysis["id"],
                "date": analysis["analysis_date"],
                "prompt": analysis["prompt"],
                "schools": school_results,
                "winner": analysis["winner"],
                "summary": analysis["summary"],
                "qualityGate": {
                    "passed": bool(analysis["quality_gate_passed"]),
                    "warnings": analysis["quality_gate_warnings"].split("\n")
                    if analysis["quality_gate_warnings"]
                    else [],
                },
                "createdAt": analysis["created_at"],
            }
