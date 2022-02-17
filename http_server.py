import socket
import json
import h2.connection
import h2.config
import metadata



def get_map(gps_location):

    if [gps_location["lat"], gps_location["lon"]] in metadata.availableGPSpoints:
        pos = metadata.availableGPSpoints.index([gps_location["lat"], gps_location["lon"]])

        if pos>=0 and pos <=87:
            return metadata.espoo_json
        if pos>=88 and pos <=208:
            return metadata.helsinki_json

    return "NOT FOUND"


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

        while True:
            data = sock.recv(65535)
            if not data:
                break

            events = conn.receive_data(data)

            headers = {}
            for event in events:

                # Recieve and process headers
                if isinstance(event, h2.events.RequestReceived):
                    
                    for _t in event.headers:
                        if _t[0] == b":method":
                            headers["method"] = _t[1]
                        elif _t[0] == b":path":
                            headers["path"] = _t[1]

                # process the actual request
                if isinstance(event, h2.events.DataReceived):
                    # check which path was requested
                    print(
                        f"request: [{headers['method']}] [{headers['path']}]\n\t [{event.data}]"
                    )
                    response_data = ""
                    if headers["path"] == b"/":
                        pass
                    # get regional map for single gps location
                    if headers["path"] == b"/getMap":
                        # TODO get_map(gps_location)
                        gps_location = json.loads(event.data.decode('utf-8'))
                        print("GPS")
                        print(gps_location)
                        response_data = get_map(gps_location)
                    # etc

                    # just return the data for now
                    self.send_dev_response(conn, event, response_data)

            data_to_send = conn.data_to_send()
            if data_to_send:
                sock.sendall(data_to_send)

    def send_dev_response(self, conn, event, response_data):
        stream_id = event.stream_id
        data = json.dumps(response_data).encode('utf-8')
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

server = HTTPServer()
server.start()
