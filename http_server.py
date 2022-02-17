import socket
import json
import h2.connection
import h2.config
import metadata
import sys


class HTTPServer:
    def __init__(self):
        """Inits the socket, start listening on 8080"""
        print("[server]: starting..")
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", 8000))
        self.sock.listen(5)

    def start(self):
        """Start listening to connections"""
        print("[server]: listening for connections..")
        while True:
            self.handle(self.sock.accept()[0])

    def handle(self, sock):
        """Handle a connection to the server

        Args:
            sock (_type_): _description_
        """
        print("[server]: new connection")
        config = h2.config.H2Configuration(client_side=False)
        conn = h2.connection.H2Connection(config=config)
        conn.initiate_connection()
        sock.sendall(conn.data_to_send())

        headers = {}
        request_data = b""

        while True:
            data = sock.recv(65535)
            if not data:
                break

            events = conn.receive_data(data)
            for event in events:

                # Recieve and process headers
                if isinstance(event, h2.events.RequestReceived):

                    for _t in event.headers:
                        if _t[0] == b":method":
                            headers["method"] = _t[1]
                        elif _t[0] == b":path":
                            headers["path"] = _t[1]
                    print(
                        f"[server]: headers received [{headers['method']}] [{headers['path']}]"
                    )

                # process the actual request data
                if isinstance(event, h2.events.DataReceived):
                    print(
                        f"[server]: data recieved [{event.data[:10]} ... len={sys.getsizeof(event.data)}]"
                    )

                    # ack that we recieved a chunk of the data
                    conn.acknowledge_received_data(
                        event.flow_controlled_length, event.stream_id
                    )

                    # determine operations based on path in headers

                    # get regional map for single gps location
                    if headers["path"] == b"/getMap":
                        gps_location = json.loads(event.data.decode("utf-8"))
                        print("[server]: gps location recieved")
                        response_data = self.get_map(gps_location)
                        # if location was not found, return HTTP 400
                        if "error" in response_data.keys():
                            self.send_error_response(conn, event, response_data)
                            continue

                    # get all maps for a trace
                    if headers["path"] == b"/getMaps":
                        gps_trace = json.loads(event.data.decode("utf-8"))
                        print("[server]: gps trace recieved")
                        response_data = {"trace": gps_trace}

                        # send first map
                        # push the rest (close stream)

                    # save a photo along with GPS location
                    if headers["path"] == b"/savePhoto":
                        request_data += event.data
                        try:
                            # keep getting more data until full dict gotten
                            data = json.loads(request_data.decode("utf-8"))

                            # all data gotten
                            gps_location = data["gps_location"]
                            photo_bytes = data["photo"]

                            if headers["method"] == b"POST":
                                result = self.save_picture(gps_location, photo_bytes)
                            elif headers["method"] == b"PUT":
                                result = "overwritten"
                            else:
                                result = "invalid method"

                            response_data = {"result": result}

                            # send a response indicating a succesfull request, along with the data
                            self.send_successfull_response(conn, event, response_data)

                        # if not full dict, keep getting data
                        except json.decoder.JSONDecodeError:
                            pass

            data_to_send = conn.data_to_send()
            if data_to_send:
                sock.sendall(data_to_send)

    def send_successfull_response(self, conn, event, response_data):
        """Send a successfull (HTTP 200) response"""

        stream_id = event.stream_id
        data = json.dumps(response_data).encode("utf-8")
        conn.send_headers(
            stream_id=stream_id,
            headers=[
                (":status", "200"),
                ("server", "basic-h2-server/1.0"),
                ("content-length", str(len(data))),
                ("content-type", "application/json"),
            ],
        )
        conn.send_data(stream_id=stream_id, data=data, end_stream=True)

    def send_error_response(self, conn, event, response_data):
        stream_id = event.stream_id
        data = json.dumps(response_data).encode("utf-8")
        conn.send_headers(
            stream_id=stream_id,
            headers=[
                (":status", "400"),
                ("server", "basic-h2-server/1.0"),
                ("content-length", str(len(data))),
                ("content-type", "application/json"),
            ],
        )
        conn.send_data(stream_id=stream_id, data=data, end_stream=True)

    def get_map(self, gps_location: dict):
        if [gps_location["lat"], gps_location["lon"]] in metadata.availableGPSpoints:
            pos = metadata.availableGPSpoints.index(
                [gps_location["lat"], gps_location["lon"]]
            )

            if pos >= 0 and pos <= 87:
                return metadata.espoo_json
            if pos >= 88 and pos <= 208:
                return metadata.helsinki_json

        print("[server]: invalid gps location")
        return {"error": "location not found"}

    def get_maps(self, gps_trace: list):

        # TODO: find and return all maps on the trajectory
        pass

    def save_picture(self, gps_location: dict, photo_bytes: bytes, put=False) -> str:
        """Save a photo with the corresponding GPS location to the server

        Args:
            gps_location (dict): The gps location provided
            photo_bytes (bytes): The photo as bytes
        """
        print("[server]: photo and location recieved, saving..")

        gps_location = str(gps_location)

        with open("gps_photos.json", "r") as f:
            data = json.loads(f.read())

            # if photo for these coordinates exists and method was not put
            # dont save and inform that exists already
            if gps_location in data.keys() and not put:
                return "photo exists already"

            # else just rewrite / save the photo
            data[gps_location] = photo_bytes

        # write data back to file
        with open("gps_photos.json", "w") as f:
            f.write(json.dumps(data))

        return "photo saved"


server = HTTPServer()
server.start()
