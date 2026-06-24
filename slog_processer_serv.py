from fastapi import FastAPI, UploadFile, HTTPException
import datetime
from collections import Counter
import json
from dotenv import load_dotenv
import os
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI
from contextlib import asynccontextmanager
from pprint import pprint



load_dotenv()

CHUNK_SIZE = 64 * 1024 
DATABASE_CONN_STRING = os.getenv('MONGO_URI')

async def init_database():
  db_client = AsyncIOMotorClient(DATABASE_CONN_STRING)
  return db_client

@asynccontextmanager
async def lifespan(app: FastAPI):
  app.state.db_client = await init_database()

  try:
    yield
  finally:
    app.state.db_client.close()

app = FastAPI(lifespan=lifespan)

@app.post('/upload')
async def upload_file(file: UploadFile):


  UnsupportedDetail = f"The uploaded file ({file.filename}) is either a binary format or an unsupported text encoding. Only UTF-8 encoded text streams are accepted."
  if file.content_type != "text/plain" and file.content_type != "application/octet-stream":
    raise HTTPException(status_code=415, detail=UnsupportedDetail)

  trailing_buffer = bytes('', 'utf-8')
  invalid_code_key = "Not a valid HTTP Status Code"
  response_dictionary = Counter()
  
  ct = datetime.datetime.now()

  def process_log_line(line):
    try:
      line = str(line, 'utf-8')
      line = line.split("\"")
      if len(line) != 3 or len(line[0].split()) + len(line[2].split()) != 7 or len(line[1].split()) != 3:
        response_dictionary["MalformedLog"] += 1
        return
      http_status_code = int(line[2].split()[0])
      if http_status_code >= 100 and http_status_code < 600:
#        print('code: ', http_status_code)
        response_dictionary[str(http_status_code)] += 1
      else:
        response_dictionary[invalid_code_key] += 1
#        print('invalid code: ', http_status_code)
    except UnicodeDecodeError:
      raise HTTPException(status_code=415, detail=UnsupportedDetail)
#      response_dictionary["CorruptLine"] += 1
    except ValueError:
      response_dictionary["ValueError"] += 1


  while chunk := await file.read(CHUNK_SIZE):
    trailing_buffer += chunk
    aux_line_list = trailing_buffer.split(b'\n')
    
    for idx in range(len(aux_line_list) - 1):
      process_log_line(aux_line_list[idx])

    trailing_buffer = aux_line_list[-1]

  if trailing_buffer != b'':
    process_log_line(trailing_buffer)

  # print('returned json: ', json.dumps(response_dictionary))
  
  
  log_to_insert = { "filename": file.filename, "timestamp": ct.timestamp(), "logs": response_dictionary }
  logs_collection = app.state.db_client.logs_api.processed_logs
  result = await logs_collection.insert_one(log_to_insert)
  log_to_insert["receipt_id"] = str(result.inserted_id)
  pprint(log_to_insert)
  del log_to_insert["_id"]
  pprint(log_to_insert)
  return log_to_insert


@app.get('/')
async def say_hello_world():
  return { "message": "Hello World! What's up?" }

@app.get('/hello/{name}')
async def say_hello_name(name: str = "Default"):
  # inofensive line
  # inofensive change
  message = "Hello " + name + "!"
  return { "message": message }



@app.get('/hello-database/{name}')
async def say_hello_database(name: str):
  try:
    #conn = MongoClient(DATABASE_CONN_STRING)
    #info = conn.server_info()
    #conn.close()
    ct = datetime.datetime.now()
    await app.state.db_client.admin.command('ping')
    my_db = app.state.db_client.logs_api
    my_collection = my_db.test_monger
    await my_collection.insert_one({"nombre": name, "date time": str(ct)})
    new_data = await my_collection.find_one({"nombre": name})
    if new_data:
      new_data["_id"] = str(new_data["_id"])
    dblist = await app.state.db_client.list_database_names()
    return { "message": "database says hello", "list of databases": dblist, "inserted data": new_data}
  except Exception as e:
    return { "message": "database cant say hello", "error": str(e) }



