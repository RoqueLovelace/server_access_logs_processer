from io import BytesIO
from slog_processer_serv import app
import asyncio
import pytest
import json
from motor.motor_asyncio import AsyncIOMotorClient
import pytest_asyncio
from dotenv import load_dotenv
import os
from httpx2 import AsyncClient, ASGITransport
from pprint import pprint

load_dotenv()
#
#binary_buffer.write(b'hello')
#
#result_bytes = binary_buffer.getvalue()
#
#print(result_bytes)


@pytest_asyncio.fixture
async def client():
  app.state.db_client = AsyncIOMotorClient(os.getenv('MONGO_URI_TEST'))
  async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
    yield ac
  app.state.db_client.close()

@pytest.mark.asyncio
async def test_say_hello(client):
  response = await client.get("/")
  assert response.status_code == 200
  assert response.json() == {"message": "Hello World! What's up?"}


@pytest.mark.asyncio
async def test_say_hello_name(client):
  response = await client.get("/hello/chris")
  assert response.status_code == 200
  assert response.json() == {"message": "Hello " + "chris" + "!"}

@pytest.mark.asyncio
async def test_upload_fine_file(client):
  buffer = BytesIO()

  # log with no problems. Should add one to 200 element in the response body
  buffer.write(b'127.0.0.1 - - [01/May/2025:07:20:10 +0000] \"GET /index.html HTTP/1.1\" 200 9481')

  # incomplete log. Should add one to MalformedLog element in the response body
  buffer.write(b'\n127.0.0.1 - [01/May/2025:07:20:10 +0000] \"GET /index.html HTTP/1.1\" 200 9481')

  # log with status code out of range. Should add one to "Not a valid HTTP Status Code" element in the response body
  buffer.write(b'\n127.0.0.1 - - [01/May/2025:07:20:10 +0000] \"GET /index.html HTTP/1.1\" 1000 9481')


  files = { "file": ("log_test.txt", buffer, "text/plain") }
  response = await client.post("/upload", files=files)


  audit = response.json()
#  audit = json.loads(response.json())
  print("audit: ")
  pprint(audit)

  assert response.status_code == 200
#  assert "\'MalformedLog\': 1" in response.json()
  assert audit["logs"]["200"] == 1
  assert audit["logs"]["MalformedLog"] == 1
  assert audit["logs"]["Not a valid HTTP Status Code"] == 1


@pytest.mark.asyncio
async def test_upload_binary_file(client):
  buffer = BytesIO()

  # log with no UTF-8 bytes. Should trigger a 415 response 
  buffer.write(b'\xff')
  buffer.write(b'127.0.0.1 - - [01/May/2025:07:20:10 +0000] \"GET /index.html HTTP/1.1\" 200 9481')


  files = { "file": ("log_test.txt", buffer, "text/plain") }
  response = await client.post("/upload", files=files)

  assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_bad_type_file(client):
  buffer = BytesIO()

  # any content
  buffer.write(b'127.0.0.1 - - [01/May/2025:07:20:10 +0000] \"GET /index.html HTTP/1.1\" 200 9481')


  files = { "file": ("log_test.txt", buffer, "text/html") }
  response = await client.post("/upload", files=files)
  assert response.status_code == 415
