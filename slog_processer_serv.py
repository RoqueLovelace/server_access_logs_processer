from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from collections import Counter
import json

app = FastAPI()
CHUNK_SIZE = 64 * 1024 

@app.post('/upload')
async def upload_file(file: UploadFile):

  UnsupportedDetail = f"The uploaded file (" + file.filename + ") is either a binary format or an unsupported text encoding. Only UTF-8 encoded text streams are accepted."
  if file.content_type != "text/plain" and file.content_type != "application/octet-stream":
    raise HTTPException(status_code=415, detail=UnsupportedDetail)

  trailing_buffer = bytes('', 'utf-8')
  invalid_code_key = "Not a valid HTTP Status Code"
  response_dictionary = Counter()


  def process_log_line(line):
    try:
      line = str(line, 'utf-8')
      line = line.split("\"")
        return
      http_status_code = int(line[2].split()[0])
      if http_status_code >= 100 and http_status_code < 600:
#        print('code: ', http_status_code)
        response_dictionary[http_status_code] += 1
      else:
        response_dictionary[invalid_code_key] += 1
#        print('invalid code: ', http_status_code)
    except UnicodeDecodeError:
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

  print('returned json: ', json.dumps(response_dictionary))
  return response_dictionary


@app.get('/')
async def say_hello_world():
  return { "message": "Hello World!" }

@app.get('/hello/{name}')
async def say_hello_name(name: str = "Default"):
  # inofensive line
  # inofensive change
  message = "Hello " + name + "!"
  return { "message": message }
