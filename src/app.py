"""
API do Sistema de Gestão da Mergington High School

Uma aplicação FastAPI bem simples que permite aos estudantes visualizar e se
inscrever em atividades extracurriculares da Mergington High School.
"""

import hashlib
import json
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
import os

app = FastAPI(title="Mergington High School API",
              description="API para visualizar e se inscrever em atividades extracurriculares")

# Monta o diretório de arquivos estáticos
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

with (current_dir / "teachers.json").open(encoding="utf-8") as teachers_file:
    teachers = json.load(teachers_file)

active_tokens = {}
bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


def _password_hash(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), iterations
    ).hex()


def require_teacher(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Autenticação de professor necessária",
            headers={"WWW-Authenticate": "Bearer"},
        )

    teacher = active_tokens.get(credentials.credentials)
    if teacher is None:
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return teacher

# Banco de dados de atividades em memória
activities = {
    "Chess Club": {
        "description": "Aprenda estratégias e dispute torneios de xadrez",
        "schedule": "Sextas-feiras, 15h30 - 17h00",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Aprenda os fundamentos de programação e construa projetos de software",
        "schedule": "Terças e quintas-feiras, 15h30 - 16h30",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Educação física e atividades esportivas",
        "schedule": "Segundas, quartas e sextas-feiras, 14h00 - 15h00",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Entre para o time de futebol da escola e dispute partidas",
        "schedule": "Terças e quintas-feiras, 16h00 - 17h30",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Treine e jogue basquete com o time da escola",
        "schedule": "Quartas e sextas-feiras, 15h30 - 17h00",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore sua criatividade por meio da pintura e do desenho",
        "schedule": "Quintas-feiras, 15h30 - 17h00",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Atue, dirija e produza peças e apresentações",
        "schedule": "Segundas e quartas-feiras, 16h00 - 17h30",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Resolva problemas desafiadores e participe de competições de matemática",
        "schedule": "Terças-feiras, 15h30 - 16h30",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Desenvolva habilidades de oratória e argumentação",
        "schedule": "Sextas-feiras, 16h00 - 17h30",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/auth/login")
def login(credentials: LoginRequest):
    teacher = teachers.get(credentials.username)
    if teacher is None:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

    candidate_hash = _password_hash(
        credentials.password, teacher["salt"], teacher["iterations"]
    )
    if not secrets.compare_digest(candidate_hash, teacher["password_hash"]):
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

    token = secrets.token_urlsafe(32)
    active_tokens[token] = credentials.username
    return {
        "access_token": token,
        "token_type": "bearer",
        "teacher": credentials.username,
    }


@app.post("/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Autenticação de professor necessária",
            headers={"WWW-Authenticate": "Bearer"},
        )

    active_tokens.pop(credentials.credentials, None)
    return {"message": "Sessão encerrada"}


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str, email: str, _teacher: str = Depends(require_teacher)
):
    """Inscreve um estudante em uma atividade"""
    # Valida se a atividade existe
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")

    # Obtém a atividade específica
    activity = activities[activity_name]

    # Valida se o estudante já não está inscrito
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Estudante já está inscrito"
        )

    # Adiciona o estudante
    activity["participants"].append(email)
    return {"message": f"{email} inscrito em {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str, email: str, _teacher: str = Depends(require_teacher)
):
    """Cancela a inscrição de um estudante em uma atividade"""
    # Valida se a atividade existe
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")

    # Obtém a atividade específica
    activity = activities[activity_name]

    # Valida se o estudante está inscrito
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Estudante não está inscrito nesta atividade"
        )

    # Remove o estudante
    activity["participants"].remove(email)
    return {"message": f"Inscrição de {email} em {activity_name} cancelada"}
