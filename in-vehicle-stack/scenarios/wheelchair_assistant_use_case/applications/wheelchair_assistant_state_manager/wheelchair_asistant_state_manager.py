import json
import logging
import os
import threading
import time
import socket
from typing import Tuple

import grpc
from google.protobuf.json_format import Parse
from google.protobuf.internal.decoder import _DecodeVarint
from google.protobuf.internal.encoder import _VarintBytes

import ank.ankaios_pb2 as ank
import digital_twin.digital_twin_get_provider_pb2 as digital_twin
import digital_twin.digital_twin_get_provider_pb2_grpc as digital_twin_grpc

ANKAIOS_CONTROL_INTERFACE_BASE_PATH = "/run/ankaios/control_interface"
WAITING_TIME_IN_SEC = 5


def create_logger():
    """Create a logger with custom format and default log level."""
    formatter = logging.Formatter('%(asctime)s %(message)s', datefmt="%FT%TZ")
    logger = logging.getLogger("custom_logger")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

def test(body):
    with grpc.insecure_channel("0.0.0.0:5010", [("GRPC_ARG_SOCKET_FACTORY","grpc.socket_factory")]) as channel:
        stub = digital_twin_grpc.DigitalTwinGetProviderStub(channel)
        try:
            # Führe die Anfrage aus
            response = stub.Get(digital_twin.GetRequest(entity_id="dtmi:sdv:Trailer:IsTrailerConnected;1"))
            print("Response:", response)
        except grpc.RpcError as e:
            print("GRPC Error:", e.details())

#
# def send_byte_stream_and_receive_response(host: str, port: int, data: bytes, buffer_size: int = 1024) -> Tuple[bool, bytes]:
#     """
#     Sends a byte stream over a TCP socket to a specified host and port and waits for a response.
#
#     Args:
#     host (str): The hostname or IP address of the destination.
#     port (int): The port number of the destination.
#     data (bytes): The byte stream to be sent.
#     buffer_size (int): The maximum amount of data to be received at once, in bytes.
#
#     Returns:
#     Tuple[bool, str]: A tuple containing a boolean indicating success or failure,
#                       and a string message detailing the response or error.
#     """
#     try:
#         with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#             s.connect((host, port))
#             s.sendall(data)
#             response = s.recv(buffer_size)
#             return (True, response)
#     except Exception as e:
#         return (False, f"Error: {e}")
#
# def send_grpc_request(body: str) -> str:
#     """
#     Sends a gRPC request using HTTP/2 and protobuf.
#
#     Args:
#     script_dir (str): Directory where the .proto files are located.
#     body (str): JSON-formatted string to send as the request body.
#
#     Returns:
#     str: The output from the gRPC service or an error message.
#     """
#
#     # Read server address from environment variable or use default
#     server_address = os.environ.get('GRPC_SERVER', '0.0.0.0:5010')
#
#     # Deserialize the JSON body into the protobuf message
#     request_data = json.loads(body)
#     request = digital_twin.GetRequest(**request_data)
#
#     # Serialize the request to protobuf binary format
#     serialized_request = request.SerializeToString()
#     (result, response) = send_byte_stream_and_receive_response("0.0.0.0", 5010, request.SerializeToString())
#     if result is True:
#         property_value = digital_twin.GetResponse().ParseFromString(response)
#         logging.info(f"property_value={property_value}")
#     else:
#         logger.error(f"Error while getting property_value {response}")

def create_update_workload_request():
    """Create the StateChangeRequest containing an UpdateStateRequest
    that contains the details for adding the new workload and
    the update mask to add only the new workload.
    """

    return ank.StateChangeRequest(
        updateState=ank.UpdateStateRequest(
            newState=ank.CompleteState(
                currentState=ank.State(
                    workloads={
                        "dynamic_hello": ank.Workload(
                            agent="agent_A",
                            runtime="podman",
                            restart=True,
                            updateStrategy=ank.AT_MOST_ONCE,
                            runtimeConfig="image: docker.io/library/hello-world:latest")
                    }
                )
            ),
            updateMask=["currentState.workloads.dynamic_hello"]
        )
    )


def create_request_complete_state_request():
    """Create a StateChangeRequest containing a RequestCompleteState
    for querying the workload states.
    """

    return ank.StateChangeRequest(
        requestCompleteState=ank.RequestCompleteState(
            requestId="request_id",
            fieldMask=["workloadStates"]
        )
    )


def read_from_control_interface():
    """Reads from the control interface input fifo and prints the workload states."""

    with open(f"{ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/input", "rb") as f:

        while True:
            varint_buffer = b''  # Buffer for reading in the byte size of the proto msg
            while True:
                next_byte = f.read(1)  # Consume byte for byte
                if not next_byte:
                    break
                varint_buffer += next_byte
                if next_byte[
                    0] & 0b10000000 == 0:  # Stop if the most significant bit is 0 (indicating the last byte of the varint)
                    break
            msg_len, _ = _DecodeVarint(varint_buffer, 0)  # Decode the varint and receive the proto msg length

            msg_buf = b''  # Buffer for the proto msg itself
            for _ in range(msg_len):
                next_byte = f.read(1)  # Read exact amount of byte according to the calculated proto msg length
                if not next_byte:
                    break
                msg_buf += next_byte
            execution_request = ank.ExecutionRequest()
            execution_request.ParseFromString(msg_buf)  # Deserialize the received proto msg
            logger.info(
                f"Receiving ExecutionRequest containing the workload states of the current state:\nExecutionRequest {{\n{execution_request}}}\n")


def write_to_control_interface():
    """Writes a StateChangeRequest into the control interface output fifo
    to add the new workload dynamically and every 30 sec another StateChangeRequest
    to request the workload states.
    """

    with open(f"{ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/output", "ab") as f:
        update_workload_request = create_update_workload_request()
        update_workload_request_byte_len = update_workload_request.ByteSize()  # Length of the msg
        proto_update_workload_request_msg = update_workload_request.SerializeToString()  # Serialized proto msg

        logger.info(
            f"Sending StateChangeRequest containing details for adding the dynamic workload \'dynamic_nginx\':\nStateChangeRequest {{\n{update_workload_request}}}\n")
        f.write(_VarintBytes(update_workload_request_byte_len))  # Send the byte length of the proto msg
        f.write(proto_update_workload_request_msg)  # Send the proto msg itself
        f.flush()

        request_complete_state = create_request_complete_state_request()
        request_complete_state_byte_len = request_complete_state.ByteSize()  # Length of the msg
        proto_request_complete_state_msg = request_complete_state.SerializeToString()  # Serialized proto msg

        while True:
            logger.info(
                f"Sending StateChangeRequest containing details for requesting all workload states:\nStateChangeRequest {{{request_complete_state}}}\n")
            f.write(_VarintBytes(request_complete_state_byte_len))  # Send the byte length of the proto msg
            f.write(proto_request_complete_state_msg)  # Send the proto msg itself
            f.flush()
            time.sleep(WAITING_TIME_IN_SEC)  # Wait until sending the next RequestCompleteState to avoid spamming...


if __name__ == '__main__':
    logger = create_logger()
    test('{"entity_id": "dtmi:sdv:Trailer:IsTrailerConnected;1"}')
    # read_thread = threading.Thread(target=read_from_control_interface)
    # read_thread.start()
    #
    # write_to_control_interface()
    #
    # read_thread.join()
    exit(0)
