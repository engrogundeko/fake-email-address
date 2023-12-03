import json
from datetime import datetime, timedelta

from anyio import to_thread
from faker import Faker
from typing import Dict, Any, Callable
from jinja2 import Environment, FileSystemLoader


template_env = Environment(loader=FileSystemLoader("templates"))


class FakeEmailAddress:
    async def read_body(self, receive: Callable):
        body = b""
        more_body = True

        while more_body:
            message = await receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)

        return body

    async def post(self, scope: Dict[str, Any], send: Callable):
        if scope["path"] == "/":
            response = {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/html")],
            }
            await send(response)
            content = await self.render_template("index.html", context={})

            response = {"type": "http.response.body", "body": content.encode("utf-8")}
            await send(response)

        elif scope["path"] == "/generate-email":
            disposable_email = await to_thread.run_sync(self.generate_database_entry)
            response = {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/html")],
            }
            await send(response)
            content = json.dumps({**disposable_email}, default=self.json_serialization)
            response = {
                "type": "http.response.body",
                "body": content.encode("utf-8"),
            }
            await send(response)

    async def websocket():
        ...

    async def get():
        ...

    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable):
        assert scope["type"] == "http"
        body = await self.read_body(receive)

        if scope["method"] == "POST":
            await self.post(scope, send)

    def generate_database_entry(self) -> Dict[str, str]:
        fake = Faker()
        database: dict = {}
        database["email"] = fake.email()
        database["created_at"] = datetime.now()
        database["expired_at"] = database["created_at"] + timedelta(minutes=10)
        database["success"] = True
        return database

    async def render_template(self, template_name, **context):
        template_loader = FileSystemLoader(searchpath="html_template")
        template_env = Environment(loader=template_loader)
        template = template_env.get_template(template_name)

        return template.render(context)

    def json_serialization(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        raise TypeError(
            f"Object of type {obj.__class__.__name__} is not JSON serializable"
        )


app = FakeEmailAddress()
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
