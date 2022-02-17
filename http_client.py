import socket
import h2.connection
import h2.config
import h2.events
import socket


class HTTPClient:
    """Client for the http connection and requests"""

    def __init__(self, server, port):

        self.SERVER_NAME = server
        self.SERVER_PORT = port

    def open_connection(self):
        """Open a connection to the server"""
        socket.setdefaulttimeout(15)

        # open a socket to the server
        self.socket = socket.create_connection((self.SERVER_NAME, self.SERVER_PORT))

        self.connection = h2.connection.H2Connection()
        self.connection.initiate_connection()
        self.socket.sendall(self.connection.data_to_send())

    def __enter__(self):
        self.open_connection()
        return self

    def __exit__(self, exc_type, exc_value, trace):
        self.close_connection()

    def send_request(self, headers, data):
        self.open_connection()
        response = self.__send_request(headers, data, 1)
        self.close_connection()

        return response

    def __send_request(self, headers_to_send, data_to_send, stream_id):
        """Send a request to the server."""

        if headers_to_send:
            self.connection.send_headers(stream_id, headers_to_send)

        self.connection.send_data(stream_id, data_to_send)
        self.socket.sendall(self.connection.data_to_send())

        body = b""
        response_stream_ended = False
        while not response_stream_ended:
            # read raw data from the self.socket
            data = self.socket.recv(65536 * 1024)
            if not data:
                break

            # feed raw data into h2, and process resulting events
            events = self.connection.receive_data(data)
            for event in events:
                if isinstance(event, h2.events.DataReceived):
                    # update flow control so the server doesn't starve us
                    self.connection.acknowledge_received_data(
                        event.flow_controlled_length, event.stream_id
                    )
                    # more response body data received
                    body += event.data
                if isinstance(event, h2.events.StreamEnded):
                    # response body completed, let's exit the loop
                    print("stream closed")
                    response_stream_ended = True
                    break

            # send any pending data to the server
            self.socket.sendall(self.connection.data_to_send())

        return body.decode()

    def close_connection(self):
        # tell the server we are closing the h2 connection
        self.connection.close_connection()
        self.socket.sendall(self.connection.data_to_send())

        # close the self.socket
        self.socket.close()
