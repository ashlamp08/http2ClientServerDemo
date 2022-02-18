from http_client import HTTPClient
import json
import time
import metadata


def second(client):
    """
    2)
    Select a GPS location from the GPS trace we provide, and send a request for a regional road
    map from the HTTP client to the server. The GPS location is indicated in the request. The
    server should send the corresponding road map back to the client
    """

    # headers and body for the request
    headers = [
        (":method", "GET"),
        (":path", "/getMap"),
        (":authority", "localhost"),
        (":scheme", "https"),
    ]
    request_body = {"lat": 60.17000859999999, "lon": 24.9389777}

    # GET, print response
    response = client.send_request(headers, json.dumps(request_body).encode("utf-8"))
    print(response)

    input("2: (invalid gps)")

    """
    2)
    Additionally, the server can handle the cases
    where the map files are not available or the
    GPS location is invalid. 
    """
    # headers and body for the request
    headers = [
        (":method", "GET"),
        (":path", "/getMap"),
        (":authority", "localhost"),
        (":scheme", "https"),
    ]
    request_body = {"lat": 1, "lon": 1}

    # GET, print response
    response = client.send_request(headers, json.dumps(request_body).encode("utf-8"))
    print(response)


def third(client):
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
        (":path", "/getMapFromTrace"),
        (":authority", "localhost"),
        (":scheme", "https"),
    ]
    request_body = [
        [60.18314587645695, 24.831518950092683],
        [60.183115400000005, 24.831577100000004],
        [60.18296499999999, 24.831824800000003],
        [60.1827219, 24.832274299999998],
        [60.170473699999995, 24.944638299999998],
        [60.170562999999994, 24.944929199999997],
    ]

    response, push = client.send_request(
        headers, json.dumps(request_body).encode("utf-8")
    )

    print(response)

    # print(push)

    for i, gps in enumerate(request_body):
        if i == 0:
            continue
        time.sleep(3)
        path = str("/getMap?lat=" + str(gps[0]) + "&lon=" + str(gps[1]))
        print(push[path])


def fourth(client):
    """
    4)
    Select a GPS location and its corresponding photo from the materials we provide. Send the
    photo with GPS location to the server. Show that the server has received the data
    successfully. If you have implemented the feature in two ways (POST vs. PUT), please
    demonstrate both.
    """

    # POST
    headers = [
        (":method", "POST"),
        (":path", "/savePhoto"),
        (":authority", "localhost"),
        (":scheme", "https"),
    ]

    with open("example_photo.jpg", "rb") as image:
        f = image.read()
        photo = str(bytearray(f))

    request_body = {"gps_location": [60.1819769, 24.824864], "photo": photo}
    response = client.send_request(headers, json.dumps(request_body).encode("utf-8"))
    print(response)

    input("4) Put:")
    # PUT
    headers = [
        (":method", "PUT"),
        (":path", "/savePhoto"),
        (":authority", "localhost"),
        (":scheme", "https"),
    ]

    with open("example_photo_2.jpg", "rb") as image:
        f = image.read()
        photo = str(bytearray(f))

    request_body = {"gps_location": [60.1819769, 24.824864], "photo": photo}
    response = client.send_request(headers, json.dumps(request_body).encode("utf-8"))
    print(response)


client = HTTPClient("localhost", 8000)
input("2:")
second(client)
input("3:")
third(client)
input("4:")
fourth(client)
