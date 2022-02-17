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
2)
Select a GPS location from the GPS trace we provide, and send a request for a regional road
map from the HTTP client to the server. The GPS location is indicated in the request. The
server should send the corresponding road map back to the client
"""
requestBody = {"lat": 60.17000859999999, "lon": 24.9389777}

response = client.send_request(headers, json.dumps(requestBody).encode("utf-8"))
print(response)

input()

"""
3)
Send a request for road maps including a trace of GPS locations from the HTTP client to the
server. The server returns a regional road map for the first GPS location in the trace
immediately. After that, the server pushes the regional maps corresponding to the following
GPS locations. The client fetches the next regional map when it is entering a new region. If
your client can decide when to fetch the next map one by one based on the current location
of the vehicle, please configure the moving speed and demonstrate that function. 
"""

headers = [
    (":method", "GET"),
    (":path", "/getMaps"),
    (":authority", "localhost"),
    (":scheme", "https"),
]
response = client.send_request(headers, b"data 2")
print(response)


"""
4)
Select a GPS location and its corresponding photo from the materials we provide. Send the
photo with GPS location to the server. Show that the server has received the data
successfully. If you have implemented the feature in two ways (POST vs. PUT), please
demonstrate both. 
"""
