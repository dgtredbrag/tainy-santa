import secrets, string
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select
from .db import Base, engine, get_db
from .models import User, Game, Member, Profile, Restriction, Drawing, Assignment, Chat, Message
from .schemas import Credentials, GameCreate, JoinGame, ProfileInput, RestrictionInput, MessageInput
from .security import hash_password, verify_password, create_token, decode_token
from .draw import generate_draw, validate_draw

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Тайный Санта API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Требуется авторизация")
    try:
        user_id = decode_token(authorization[7:])
    except Exception:
        raise HTTPException(401, "Недействительный токен")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, "Пользователь не найден")
    return user

def get_member(db, game_id, user_id):
    member = db.scalar(select(Member).where(Member.game_id == game_id, Member.user_id == user_id))
    if not member:
        raise HTTPException(403, "Вы не участник этой игры")
    return member

def require_admin(db, game, user):
    if game.admin_user_id != user.id:
        raise HTTPException(403, "Только администратор игры")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/v1/auth/register")
def register(data: Credentials, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(409, "Этот email уже зарегистрирован")
    user = User(email=data.email.lower(), password_hash=hash_password(data.password))
    db.add(user); db.commit(); db.refresh(user)
    return {"access_token": create_token(user.id), "token_type": "bearer"}

@app.post("/api/v1/auth/login")
def login(data: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Неверный email или пароль")
    return {"access_token": create_token(user.id), "token_type": "bearer"}

@app.post("/api/v1/games")
def create_game(data: GameCreate, user=Depends(current_user), db: Session=Depends(get_db)):
    code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    game = Game(title=data.title, invite_code=code, admin_user_id=user.id)
    db.add(game); db.flush()
    db.add(Member(game_id=game.id, user_id=user.id, is_admin=True))
    db.commit()
    return {"id": game.id, "title": game.title, "invite_code": code, "status": game.status}

@app.post("/api/v1/games/join")
def join_game(data: JoinGame, user=Depends(current_user), db: Session=Depends(get_db)):
    game = db.scalar(select(Game).where(Game.invite_code == data.invite_code))
    if not game: raise HTTPException(404, "Игра не найдена")
    if game.status != "registration": raise HTTPException(409, "Регистрация закрыта")
    if db.scalar(select(Member).where(Member.game_id == game.id, Member.user_id == user.id)):
        raise HTTPException(409, "Вы уже участвуете")
    db.add(Member(game_id=game.id, user_id=user.id)); db.commit()
    return {"game_id": game.id, "message": "Вы присоединились к игре"}

@app.put("/api/v1/games/{game_id}/profile")
def save_profile(game_id: str, data: ProfileInput, user=Depends(current_user), db: Session=Depends(get_db)):
    game = db.get(Game, game_id)
    if not game: raise HTTPException(404, "Игра не найдена")
    if game.status != "registration": raise HTTPException(409, "Анкета закрыта после жеребьёвки")
    member = get_member(db, game_id, user.id)
    profile = db.scalar(select(Profile).where(Profile.member_id == member.id))
    if not profile:
        profile = Profile(member_id=member.id, display_name=data.display_name, wishes=data.wishes); db.add(profile)
    else:
        profile.display_name, profile.wishes = data.display_name, data.wishes
    db.commit()
    return {"success": True}

@app.get("/api/v1/games/{game_id}/members")
def list_members(game_id: str, user=Depends(current_user), db: Session=Depends(get_db)):
    game = db.get(Game, game_id)
    if not game: raise HTTPException(404, "Игра не найдена")
    require_admin(db, game, user)
    members = db.scalars(select(Member).where(Member.game_id == game_id)).all()
    return [{"member_id": m.id, "has_profile": db.scalar(select(Profile).where(Profile.member_id == m.id)) is not None}
            for m in members]

@app.post("/api/v1/games/{game_id}/restrictions")
def add_restriction(game_id: str, data: RestrictionInput, user=Depends(current_user), db: Session=Depends(get_db)):
    game = db.get(Game, game_id)
    if not game: raise HTTPException(404, "Игра не найдена")
    require_admin(db, game, user)
    if game.status != "registration": raise HTTPException(409, "Ограничения закрыты")
    a, b = db.get(Member, data.santa_member_id), db.get(Member, data.recipient_member_id)
    if not a or not b or a.game_id != game_id or b.game_id != game_id or a.id == b.id:
        raise HTTPException(400, "Некорректная пара участников")
    db.add(Restriction(game_id=game_id, santa_member_id=a.id, recipient_member_id=b.id))
    try: db.commit()
    except Exception: db.rollback(); raise HTTPException(409, "Такое ограничение уже существует")
    return {"success": True}

@app.post("/api/v1/games/{game_id}/draw")
def draw(game_id: str, user=Depends(current_user), db: Session=Depends(get_db)):
    game = db.scalar(select(Game).where(Game.id == game_id).with_for_update())
    if not game: raise HTTPException(404, "Игра не найдена")
    require_admin(db, game, user)
    if game.status != "registration": raise HTTPException(409, "Жеребьёвка уже проводилась или игра закрыта")
    members = db.scalars(select(Member).where(Member.game_id == game_id)).all()
    profiles = {p.member_id for p in db.scalars(select(Profile).where(Profile.member_id.in_([m.id for m in members]))).all()}
    if len(members) < 2: raise HTTPException(400, "Нужно минимум два участника")
    if any(m.id not in profiles for m in members):
        raise HTTPException(409, "Не все участники заполнили анкеты")
    restrictions = {(r.santa_member_id, r.recipient_member_id)
                    for r in db.scalars(select(Restriction).where(Restriction.game_id == game_id)).all()}
    result = generate_draw([m.id for m in members], restrictions)
    if not result or not validate_draw([m.id for m in members], restrictions, result):
        raise HTTPException(422, "NO_VALID_DISTRIBUTION: проверьте запрещённые пары")
    try:
        drawing = Drawing(game_id=game_id, status="completed"); db.add(drawing); db.flush()
        for santa, recipient in result.items():
            assignment = Assignment(drawing_id=drawing.id, santa_member_id=santa, recipient_member_id=recipient)
            db.add(assignment); db.flush(); db.add(Chat(assignment_id=assignment.id))
        game.status = "active"
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(500, "Не удалось сохранить жеребьёвку; изменения отменены")
    return {"success": True, "status": "completed", "participants_count": len(members)}

@app.get("/api/v1/games/{game_id}/draw/results")
def draw_results(game_id: str, user=Depends(current_user), db: Session=Depends(get_db)):
    game = db.get(Game, game_id)
    if not game: raise HTTPException(404, "Игра не найдена")
    require_admin(db, game, user)
    drawing = db.scalar(select(Drawing).where(Drawing.game_id == game_id))
    if not drawing: raise HTTPException(404, "Жеребьёвка ещё не проводилась")
    rows = db.scalars(select(Assignment).where(Assignment.drawing_id == drawing.id)).all()
    result = []
    for row in rows:
        a, b = db.get(Profile, db.scalar(select(Profile.id).where(Profile.member_id == row.santa_member_id))), db.get(Profile, db.scalar(select(Profile.id).where(Profile.member_id == row.recipient_member_id)))
        result.append({"santa": a.display_name, "recipient": b.display_name})
    return result

@app.get("/api/v1/games/{game_id}/my-recipient")
def my_recipient(game_id: str, user=Depends(current_user), db: Session=Depends(get_db)):
    member = get_member(db, game_id, user.id)
    assignment = db.scalar(select(Assignment).join(Drawing).where(
        Drawing.game_id == game_id, Assignment.santa_member_id == member.id))
    if not assignment: raise HTTPException(404, "Подопечный пока не назначен")
    profile = db.scalar(select(Profile).where(Profile.member_id == assignment.recipient_member_id))
    return {"display_name": profile.display_name, "wishes": profile.wishes}

@app.get("/api/v1/games/{game_id}/chat")
def get_chat(game_id: str, user=Depends(current_user), db: Session=Depends(get_db)):
    member = get_member(db, game_id, user.id)
    assignment = db.scalar(select(Assignment).join(Drawing).where(
        Drawing.game_id == game_id,
        (Assignment.santa_member_id == member.id) | (Assignment.recipient_member_id == member.id)))
    if not assignment: raise HTTPException(404, "Чат не найден")
    chat = db.scalar(select(Chat).where(Chat.assignment_id == assignment.id))
    rows = db.scalars(select(Message).where(Message.chat_id == chat.id).order_by(Message.created_at)).all()
    return [{"sender_label": "Вы" if row.sender_member_id == member.id else
             ("Твой Тайный Санта" if assignment.santa_member_id == row.sender_member_id else "Твой подопечный"),
             "content": row.content, "created_at": row.created_at} for row in rows]

@app.post("/api/v1/games/{game_id}/chat")
def send_message(game_id: str, data: MessageInput, user=Depends(current_user), db: Session=Depends(get_db)):
    member = get_member(db, game_id, user.id)
    assignment = db.scalar(select(Assignment).join(Drawing).where(
        Drawing.game_id == game_id,
        (Assignment.santa_member_id == member.id) | (Assignment.recipient_member_id == member.id)))
    if not assignment: raise HTTPException(404, "Чат не найден")
    chat = db.scalar(select(Chat).where(Chat.assignment_id == assignment.id))
    msg = Message(chat_id=chat.id, sender_member_id=member.id, content=data.content)
    db.add(msg); db.commit()
    return {"success": True, "created_at": msg.created_at}
