import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from . import generator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="川麻练习")

_MAKERS = {
    "ting": generator.make_ting_problem,
    "discard": generator.make_discard_problem,
}


@app.get("/api/problem/{mode}")
def get_problem(mode: str) -> dict:
    maker = _MAKERS.get(mode)
    if maker is None:
        raise HTTPException(status_code=404, detail=f"未知模式: {mode}")
    problem = maker()
    logger.info("生成 %s 题目: %s", mode, " ".join(problem["hand"]))
    return problem


app.mount("/", StaticFiles(directory=Path(__file__).parent.parent / "static", html=True))
