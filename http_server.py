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

        def wait_for_window_update():

            body = b""
            window_updated = False
            while not window_updated:
                # read raw data from the self.socket
                data = sock.recv(65536 * 1024)
                if not data:
                    break

                # feed raw data into h2, and process resulting events
                events = conn.receive_data(data)
                for event in events:
                    if isinstance(event, h2.events.WindowUpdated):
                        window_updated = True

                # send any pending data to the server
                sock.sendall(conn.data_to_send())

        headers = {}
        request_data = b""
        trace_request_data = b""

        while True:
            data = sock.recv(65535)
            if not data:
                break

            events = conn.receive_data(data)
            for event in events:

                # Recieve and process headers
                if isinstance(event, h2.events.RequestReceived):
                    for _t in event.headers:
                        if _t[0] == ":method":
                            headers["method"] = _t[1]
                        elif _t[0] == ":path":
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
                    if headers["path"] == "/getMap":
                        gps_location = json.loads(event.data.decode("utf-8"))
                        print("[server]: gps location recieved")
                        response_data = self.get_map(
                            [gps_location["lat"], gps_location["lon"]]
                        )
                        # if location was not found, return HTTP 400
                        if "error" in response_data.keys():
                            self.send_error_response(conn, event, response_data)
                            continue
                        else:
                            self.send_successfull_response(conn, event, response_data)
                            conn.end_stream(event.stream_id)

                    # get all maps for a trace

                    if headers["path"] == "/getMapFromTrace":
                        print("[server]: gps trace recieved")
                        trace_request_data += event.data
                        # print(trace_request_data)
                        try:
                            # keep getting more data until full dict gotten
                            data = json.loads(trace_request_data.decode("utf-8"))
                            gps_trace = data
                            response_data = self.get_map(gps_trace[0])

                            # send the response to first GPS point in the trace
                            self.send_successfull_response(conn, event, response_data)

                            # send push for all the points in the trace except first
                            for idx, gps in enumerate(gps_trace):
                                if idx != 0:
                                    response = self.get_map(gps)
                                    print("[server]: pushing map for point : ", gps)
                                    # check that flow control window not closing
                                    if conn.local_flow_control_window(
                                        event.stream_id
                                    ) < sys.getsizeof(
                                        json.dumps(response).encode("utf-8")
                                    ):
                                        # send queued data and wait
                                        data_to_send = conn.data_to_send()
                                        if data_to_send:
                                            sock.sendall(data_to_send)
                                        # wait for window update
                                        print("[server]: waiting for window update")
                                        wait_for_window_update()
                                    self.send_push(
                                        conn,
                                        event,
                                        gps,
                                        json.dumps(response).encode("utf-8"),
                                    )
                                    print("[server]: pushed map for point : ", gps)

                            conn.end_stream(event.stream_id)

                        except json.decoder.JSONDecodeError:
                            pass

                    # save a photo along with GPS location
                    if headers["path"] == "/savePhoto":
                        request_data += event.data
                        try:
                            # keep getting more data until full dict gotten
                            data = json.loads(request_data.decode("utf-8"))

                            # all data gotten
                            gps_location = data["gps_location"]
                            photo_bytes = data["photo"]

                            if headers["method"] == "POST":
                                result = self.save_picture(gps_location, photo_bytes)
                            elif headers["method"] == "PUT":
                                result = self.save_picture(
                                    gps_location, photo_bytes, put=True
                                )
                            else:
                                result = "invalid method"

                            response_data = {"result": result}

                            # send a response indicating a succesfull request, along with the data
                            self.send_successfull_response(conn, event, response_data)
                            conn.end_stream(event.stream_id)

                        # if not full dict, keep getting data
                        except json.decoder.JSONDecodeError:
                            pass

            data_to_send = conn.data_to_send()
            if data_to_send:
                sock.sendall(data_to_send)

    def send_push(self, conn, event, gps_location, response):
        push_id = conn.get_next_available_stream_id()
        # request_body = event.body
        push_headers = [
            (":method", "GET"),
            (
                ":path",
                "/getMap?lat=" + str(gps_location[0]) + "&lon=" + str(gps_location[1]),
            ),
            (":authority", "localhost"),
            (":scheme", "https"),
        ]

        # for entry in event.headers:
        #     if ':path' in entry:
        #         if '/getMapFromTrace' in entry:
        #             push_headers.append((':path','/getMap?lat=' + str(gps_location[0]) + '&lon=' + str(gps_location[1])))
        #         else:
        #             return
        #     else:
        #         push_headers.append(entry)

        conn.push_stream(
            stream_id=event.stream_id,
            promised_stream_id=push_id,
            request_headers=push_headers,
        )
        response_headers = [
            (":status", "200"),
            ("server", "basic-h2-server/1.0"),
            ("content-length", str(len(response))),
            ("content-type", "application/json"),
        ]
        conn.send_headers(
            stream_id=push_id,
            headers=response_headers,
        )
        conn.send_data(stream_id=push_id, data=response, end_stream=True)

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
        conn.send_data(stream_id=stream_id, data=data, end_stream=False)

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

    def get_map(self, gps_location):
        if gps_location in metadata.availableGPSpoints:
            pos = metadata.availableGPSpoints.index(gps_location)
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
            exists = gps_location in data.keys()
            if exists and not put:
                return "photo exists already"

            # else just rewrite / save the photo
            data[gps_location] = photo_bytes

        # write data back to file
        with open("gps_photos.json", "w") as f:
            f.write(json.dumps(data))

        if exists and put:
            return "photo overwritten"

        return "photo saved"


server = HTTPServer()
server.start()
