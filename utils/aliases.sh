export REGISTRY="192.168.101.63:5000"

ROOT_DIR=$(pwd)
export KUBE_FILE_DIR="$ROOT_DIR"/kubernetes
export IMAGE_DIR="$ROOT_DIR"/images
export UTILS_DIR="$ROOT_DIR"/utils
export PATH="$PATH:$UTILS_DIR"
alias prunepods='kubectl delete pod --field-selector=status.phase==Succeeded && kubectl delete pod --field-selector=status.phase==Failed'