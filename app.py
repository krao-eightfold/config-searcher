from sonic import IngestClient, SearchClient
import logging
from fastapi import FastAPI
import uvicorn
import sys
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, HTTPException, status
import secrets
from os import getenv
import json

"""
TODO
- React UI app: https://testdriven.io/blog/fastapi-react/
"""


IN_PROD = getenv('RUNTIME') == 'prod'

COLLECTION = "8f_cfg"
BUCKET = "flat_dicts"


app = FastAPI()
security = HTTPBasic()
templates = Jinja2Templates(directory="html_templates/")
SONIC_HOST = getenv('SONIC_HOST', 'localhost')
SONIC_PORT = 1491

def get_secrets():
    secrets = json.load(open('secrets.json', 'r'))
    return (
        secrets['http_basic']['uname'],
        secrets['http_basic']['pwd'],
        secrets['sonic']['pwd']
    )

HTTP_UNAME, HTTP_PWD, SONIC_PASSWORD = get_secrets()


querycl = SearchClient(f"{SONIC_HOST}", SONIC_PORT, SONIC_PASSWORD)
ingestcl = IngestClient(f"{SONIC_HOST}", SONIC_PORT, SONIC_PASSWORD)

# configure logging with filename, function name and line numbers
logging.basicConfig(
    datefmt="%I:%M:%S %p %Z",
    format="%(levelname)s [%(asctime)s - %(filename)s:%(lineno)s::%(funcName)s]\t%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)
log = logging.getLogger(__name__)


@app.on_event("startup")
def startup_event():
    log.info("Connecting to host %s and port %s", SONIC_HOST, SONIC_PORT)
    if not ingestcl.ping():
        log.info("Ingest channel inactive.")
        sys.exit(1)

    if not querycl.ping():
        log.info("Query channel inactive.")
        sys.exit(1)

@app.on_event("shutdown")
def shutdown_event():
    querycl.quit()
    ingestcl.quit()


def validate_user(credentials: HTTPBasicCredentials = Depends(security)):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = bytes(HTTP_UNAME, "utf8")
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = bytes(HTTP_PWD, "utf8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get('/')
def read_form():
    return RedirectResponse('/search')


@app.get("/count")
def count() -> str:
    return f"Count: {ingestcl.count(COLLECTION, BUCKET)}"


@app.get("/search")
def form_get(request: Request, username: str = Depends(validate_user)):
    result = ["Enter a query to find the associated config"]
    return templates.TemplateResponse(
        'form.html',
        context={
            'request': request,
            "query": "",
            "user": username,
            'result': result,
            "index_object_count": ingestcl.count(COLLECTION, BUCKET),
        },
    )


@app.post("/search")
def form_post(request: Request, query: str = Form(...), username: str = Depends(validate_user)):
    log.info("query: %s", query)

    result = querycl.query(COLLECTION, BUCKET, query, limit=25)
    result = list(set([
        r[:r.rfind('.')] for r in result
    ]))
    # if not result:
    #     result += querycl.suggest_with_limit(COLLECTION, BUCKET, query, 25)

    log.info("query: %s, result: %s", query, result)
    return templates.TemplateResponse(
        'form.html',
        context={
            'request': request,
            "user": username,
            "query": query,
            'result': result,
            "index_object_count": ingestcl.count(COLLECTION, BUCKET),
        },
    )

if __name__ == "__main__":
    uvicorn.run("app:app", host='0.0.0.0', port=5000, log_level="info", reload=not IN_PROD)
