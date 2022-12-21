from typing import Union
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import SessionLocal, engine

# models.Base.metadata.create_all(bind=engine)

app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/clubs/{club_id}", response_model=schemas.Club)
def read_club(club_id: int, db: Session = Depends(get_db)):
    db_club = crud.get_club(db, club_id=club_id)
    if db_club is None:
        raise HTTPException(status_code=404, detail="Club not found")
    return db_club


@app.get("/competition/{competition_id}", response_model=schemas.Competition)
def read_competition(competition_id: str, db: Session = Depends(get_db)):
    db_competition = crud.get_competition(db, competition_id=competition_id)
    if db_competition is None:
        raise HTTPException(status_code=404, detail="Competition not found")
    return db_competition


@app.get("/games/{game_id}", response_model=schemas.Game)
def read_game(game_id: int, db: Session = Depends(get_db)):
    db_game = crud.get_game(db, game_id=game_id)
    if db_game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return db_game


# @app.get("/players", response_model=list[schemas.Player])
# def read_players(db: Session = Depends(get_db), skip: int = 0, limit: Union[int, None] = None):
#     """Retrieve list of players."""
#     db_player = crud.get_multi_player(db, skip=skip, limit=limit)
#     if db_player is None:
#         raise HTTPException(status_code=404, detail="some error")
#     return db_player

@app.post("/players", response_model=schemas.Player)
def create_player(item: schemas.PlayerCreate, db: Session = Depends(get_db)):
    return crud.create_player_item(db, item)


@app.get("/players/{player_id}", response_model=schemas.Player)
def read_player(player_id: int, db: Session = Depends(get_db)):
    db_player = crud.get_player(db, player_id=player_id)
    if db_player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return db_player
