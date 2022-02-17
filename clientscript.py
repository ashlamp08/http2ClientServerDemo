from http_client import HTTPClient
import json

client = HTTPClient("localhost", 8000)

headers = [
    (":method", "GET"),
    (":path", "/getMap"),
    (":authority", "localhost"),
    (":scheme", "https"),
]


"""
Select a GPS location from the GPS trace we provide, and send a request for a regional road
map from the HTTP client to the server. The GPS location is indicated in the request. The
server should send the corresponding road map back to the client
"""
requestBody = {"lat":60.170008599999, "lon":24.9389777}

response = client.send_request(headers, json.dumps(requestBody).encode('utf-8'))
print(response)

input()

"""
Send a request for road maps including a trace of GPS locations from the HTTP client to the
server. The server returns a regional road map for the first GPS location in the trace
immediately. After that, the server pushes the regional maps corresponding to the following
GPS locations. The client fetches the next regional map when it is entering a new region. If
your client can decide when to fetch the next map one by one based on the current location
of the vehicle, please configure the moving speed and demonstrate that function. 
"""

response = client.send_request(headers, b"data 2")
print(response)
