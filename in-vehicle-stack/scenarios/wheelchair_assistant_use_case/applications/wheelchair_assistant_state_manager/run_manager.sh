set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ANKAIOS_SERVER_SOCKET="0.0.0.0:25551"
ANKAIOS_SERVER_URL="http://${ANKAIOS_SERVER_SOCKET}"
ANK_BIN_DIR="${SCRIPT_DIR}/ankaios"

run_ankaios() {
  ANKAIOS_LOG_DIR="/tmp/"
  mkdir -p ${ANKAIOS_LOG_DIR}

  # Start the Ankaios server
  echo "Starting Ankaios server located in '${ANK_BIN_DIR}'."
  ${ANK_BIN_DIR}/ank-server --startup-config ${SCRIPT_DIR}/config/startupState.yaml --address ${ANKAIOS_SERVER_SOCKET} > ${ANKAIOS_LOG_DIR}/ankaios-server.log 2>&1 &

  sleep 2

  # Start an Ankaios agent
  echo "Starting Ankaios agent agent_A located in '${ANK_BIN_DIR}'."
  ${ANK_BIN_DIR}/ank-agent --name agent_A --server-url ${ANKAIOS_SERVER_URL} > ${ANKAIOS_LOG_DIR}/ankaios-agent_A.log 2>&1 &

  # Wait for any process to exit
  wait -n

  # Exit with status of process that exited first
  exit $?
}

podman build -t workload_assistant_state_manager:0.1 .

run_ankaios