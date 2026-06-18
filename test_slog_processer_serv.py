from io import BytesIO
from slog_processer_serv import app
from fastapi.testclient import TestClient
import asyncio
import pytest
import json



#
#binary_buffer.write(b'hello')
#
#result_bytes = binary_buffer.getvalue()
#
#print(result_bytes)

@pytest.fixture
def client():
  return TestClient(app)

def test_say_hello(client):
  response = client.get("/")
  assert response.status_code == 200
  assert response.json() == {"message": "Hello World!"}


def test_say_hello_name(client):
  response = client.get("/hello/chris")
  assert response.status_code == 200
  assert response.json() == {"message": "Hello " + "chris" + "!"}

def test_upload_fine_file(client):
  buffer = BytesIO()

  # log with no problems. Should add one to 200 element in the response body
  buffer.write(b'127.0.0.1 - - [01/May/2025:07:20:10 +0000] \"GET /index.html HTTP/1.1\" 200 9481')

  # incomplete log. Should add one to MalformedLog element in the response body
  buffer.write(b'\n127.0.0.1 - [01/May/2025:07:20:10 +0000] \"GET /index.html HTTP/1.1\" 200 9481')

  # log with status code out of range. Should add one to "Not a valid HTTP Status Code" element in the response body
  buffer.write(b'\n127.0.0.1 - - [01/May/2025:07:20:10 +0000] \"GET /index.html HTTP/1.1\" 1000 9481')


  files = { "file": ("log_test.txt", buffer, "text/plain") }
  response = client.post("/upload", files=files)


  audit = response.json()
#  audit = json.loads(response.json())
  print("audit: ",audit)

  assert response.status_code == 200
#  assert "\'MalformedLog\': 1" in response.json()
  assert audit["200"] == 1
  assert audit["MalformedLog"] == 1
  assert audit["Not a valid HTTP Status Code"] == 1


def test_upload_binary_file(client):
  buffer = BytesIO()

  # log with no UTF-8 bytes. Should trigger a 415 response 
  buffer.write(b'\xff')
  buffer.write(b'127.0.0.1 - - [01/May/2025:07:20:10 +0000] \"GET /index.html HTTP/1.1\" 200 9481')


  files = { "file": ("log_test.txt", buffer, "text/plain") }
  response = client.post("/upload", files=files)

  assert response.status_code == 415


def test_upload_bad_type_file(client):
  buffer = BytesIO()

  # any content
  buffer.write(b'127.0.0.1 - - [01/May/2025:07:20:10 +0000] \"GET /index.html HTTP/1.1\" 200 9481')


  files = { "file": ("log_test.txt", buffer, "text/html") }
  response = client.post("/upload", files=files)
  assert response.status_code == 415
