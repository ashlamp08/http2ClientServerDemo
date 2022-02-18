import socket
import h2.connection
import h2.config
import h2.events
import socket
import sys


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

    def __send_request(self, headers_to_send, data_to_send: bytes, stream_id):
        """Send a request to the server."""

        # send headers first
        if headers_to_send:
            self.connection.send_headers(stream_id, headers_to_send)
            self.socket.sendall(self.connection.data_to_send())

        # send data 16384 bytes at a time (max frame size)
        for i in range(0, sys.getsizeof(data_to_send), 16384):

            # check that flow control window not closing
            if self.connection.local_flow_control_window(stream_id) < 16384:
                # wait for window update
                self.wait_for_window_update()

            self.connection.send_data(stream_id, data_to_send[i : i + 16384])
            self.socket.sendall(self.connection.data_to_send())

        body = b""
        response_stream_ended = False
        active_streams = set()
        push_streams = set()
        received_data = {}
        push_path = {}
        while not response_stream_ended:
            # read raw data from the self.socket
            data = self.socket.recv(65536 * 1024)
            if not data:
                break

            # feed raw data into h2, and process resulting events
            events = self.connection.receive_data(data)
            for event in events:
                if isinstance(event, h2.events.DataReceived):
                    active_streams.add(event.stream_id)
                    # update flow control so the server doesn't starve us
                    if event.stream_id in received_data:
                        received_data[event.stream_id] += event.data
                    else:
                        received_data[event.stream_id] = b""
                        received_data[event.stream_id] += event.data

                    self.connection.acknowledge_received_data(
                        event.flow_controlled_length, event.stream_id
                    )
                if isinstance(event, h2.events.PushedStreamReceived):
                    active_streams.add(event.pushed_stream_id)
                    push_streams.add(event.pushed_stream_id)
                    active_streams.add(event.parent_stream_id)
                    for _t in event.headers:
                        if _t[0] == ":path":
                            push_path[event.pushed_stream_id] = _t[1]
                    # update flow control so the server doesn't starve us
                if isinstance(event, h2.events.StreamEnded):
                    active_streams.remove(event.stream_id)
                    # response body completed, let's exit the loop
                    if len(active_streams) == 0:
                        response_stream_ended = True
                        break

            # send any pending data to the server
            self.socket.sendall(self.connection.data_to_send())

        ## Separate push and non push

        push_part = {}

        for stream_id, resp_body in received_data.items():
            if stream_id not in push_streams:
                body = resp_body
            else:
                push_part[push_path[stream_id]] = resp_body.decode()

        return body.decode(), push_part

    def get_next_push(self):
        pass

    def wait_for_window_update(self):

        body = b""
        window_updated = False
        while not window_updated:
            # read raw data from the self.socket
            data = self.socket.recv(65536 * 1024)
            if not data:
                break

            # feed raw data into h2, and process resulting events
            events = self.connection.receive_data(data)
            for event in events:
                if isinstance(event, h2.events.WindowUpdated):
                    window_delta = event.delta
                    window_updated = True

            # send any pending data to the server
            self.socket.sendall(self.connection.data_to_send())

        return window_delta

    def listen_for_response(self):

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
                print(events)
                if isinstance(event, h2.events.DataReceived):
                    # update flow control so the server doesn't starve us
                    self.connection.acknowledge_received_data(
                        event.flow_controlled_length, event.stream_id
                    )
                    # more response body data received
                    body += event.data
                if isinstance(event, h2.events.StreamEnded):
                    # response body completed, let's exit the loop
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
