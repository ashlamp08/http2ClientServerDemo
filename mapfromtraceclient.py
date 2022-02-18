from hyper import HTTP20Connection
import time
import metadata
import json

pushes = {}

def request(conn, path, body):
    conn.request('POST', path, body=json.dumps(body).encode('utf-8'))
    r = conn.get_response()
    if r:        
        for push in conn.get_pushes():      
            pr = push.get_response()
            pushes[push.path] = pr
        return r.read()


conn = HTTP20Connection('localhost:8000',enable_push=True)

headers = json.dumps([
        (":method", "POST"),
        (":path", "/getMapFromTrace"),
        (":authority", "localhost"),
        (":scheme", "https"),
    ]).encode('utf-8')
body = metadata.trace

print(request(conn,'/getMapFromTrace', body))

for gps in metadata.trace:
    time.sleep(3)
    path = str.encode("/getMap?lat=" + str(gps[0]) + "&lon=" + str(gps[1]))
    # path = json.dumps(path).encode('utf-8')
    if path in pushes.keys:
        print(pushes[path].read())

# for p in pushes:
#     time.sleep(3)
#     print(p.read())

conn.close()