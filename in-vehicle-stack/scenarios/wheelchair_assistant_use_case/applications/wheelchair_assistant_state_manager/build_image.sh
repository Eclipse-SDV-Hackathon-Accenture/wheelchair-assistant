set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

mkdir -p digital_twin
cp ${SCRIPT_DIR}/../../interfaces/digital_twin_get_provider.proto ./digital_twin/

podman build -t workload_assistant_state_manager:0.1 ${SCRIPT_DIR}/
