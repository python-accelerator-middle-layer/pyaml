#!/usr/bin/env bash
set -Eeuo pipefail

DEFAULT_IMAGE_URI="oras://registry.synchrotron-soleil.fr/software_control_system_public/dt4acc-soleil-twin:latest"
TANGO_READY_PATTERN="Calculation heartbeat: simulator/ringsimulator/ringsimulator reachable"
EPICS_READY_PATTERN="EPICS IOC ready:"

usage() {
  cat <<'EOF'
Usage:
  start_dt4acc_twin.sh --accelerator-setup-file FILE --lattice-file FILE [options]
  start_dt4acc_twin.sh FILE.json FILE.m [options]

Required simulator input data:
  --accelerator-setup-file FILE   Accelerator setup JSON file passed to the twin.
  --lattice-file FILE             Lattice file passed to the twin.

Options:
  --mode tango|epics              Twin flavour. Default: tango.
                                  tango: Tango twin with an embedded Tango database.
                                  epics: EPICS soft-IOC twin, no database.
  --tango-host HOST               Tango mode only. Tango database host. Default: localhost.
  --tango-port PORT               Tango mode only. Tango database port. If omitted, the twin may choose it.
  --prefix PREFIX                 EPICS mode only. PV prefix. If omitted, the twin uses
                                  DT4ACC_PREFIX, then the current user name.
  --image-uri URI                 Apptainer image URI. Default: dt4acc latest ORAS image.
  --sif FILE                      Use a local SIF file instead of --image-uri.
  --log-file FILE                 Log file path. Default: mktemp under /tmp.
  --pid-file FILE                 Write the Apptainer process PID to FILE.
  --timeout SECONDS               Readiness timeout. Default: 900.
  --detach                        Exit after readiness and leave the twin running.
  -h, --help                      Show this help.

The script prints "Ready to use" when the twin reaches the readiness log line used by
the dt4acc-integration CI workflow (the calculation heartbeat in Tango mode, the
"EPICS IOC ready" line in EPICS mode). Keep this process running; press Ctrl-C to
stop the twin. With --detach, the script exits after readiness; use --pid-file
so a later step can stop the twin.
EOF
}

accelerator_setup_file=""
lattice_file=""
mode="tango"
tango_host="localhost"
tango_port=""
tango_option_given="0"
prefix=""
prefix_given="0"
image_uri="${DEFAULT_IMAGE_URI}"
sif_file=""
log_file=""
pid_file=""
timeout_seconds="900"
detach="0"
positionals=()

while (($#)); do
  case "$1" in
    --accelerator-setup-file|--setup-file)
      accelerator_setup_file="${2:-}"
      shift 2
      ;;
    --lattice-file)
      lattice_file="${2:-}"
      shift 2
      ;;
    --mode)
      mode="${2:-}"
      shift 2
      ;;
    --tango-host)
      tango_host="${2:-}"
      tango_option_given="1"
      shift 2
      ;;
    --tango-port)
      tango_port="${2:-}"
      tango_option_given="1"
      shift 2
      ;;
    --prefix)
      prefix="${2:-}"
      prefix_given="1"
      shift 2
      ;;
    --image-uri)
      image_uri="${2:-}"
      shift 2
      ;;
    --sif)
      sif_file="${2:-}"
      shift 2
      ;;
    --log-file)
      log_file="${2:-}"
      shift 2
      ;;
    --pid-file)
      pid_file="${2:-}"
      shift 2
      ;;
    --timeout)
      timeout_seconds="${2:-}"
      shift 2
      ;;
    --detach)
      detach="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while (($#)); do
        positionals+=("$1")
        shift
      done
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      positionals+=("$1")
      shift
      ;;
  esac
done

if [[ -z "${accelerator_setup_file}" && ${#positionals[@]} -ge 1 ]]; then
  accelerator_setup_file="${positionals[0]}"
fi

if [[ -z "${lattice_file}" && ${#positionals[@]} -ge 2 ]]; then
  lattice_file="${positionals[1]}"
fi

if [[ ${#positionals[@]} -gt 2 ]]; then
  echo "Too many positional arguments." >&2
  usage >&2
  exit 2
fi

if [[ -z "${accelerator_setup_file}" || -z "${lattice_file}" ]]; then
  echo "Missing required simulator input data." >&2
  usage >&2
  exit 2
fi

case "${mode}" in
  tango)
    if [[ "${prefix_given}" == "1" ]]; then
      echo "--prefix is only valid with --mode epics." >&2
      exit 2
    fi
    ready_pattern="${TANGO_READY_PATTERN}"
    ;;
  epics)
    if [[ "${tango_option_given}" == "1" ]]; then
      echo "--tango-host and --tango-port are only valid with --mode tango." >&2
      exit 2
    fi
    ready_pattern="${EPICS_READY_PATTERN}"
    ;;
  *)
    echo "--mode must be 'tango' or 'epics', got '${mode}'." >&2
    exit 2
    ;;
esac

if ! command -v apptainer >/dev/null 2>&1; then
  echo "apptainer is required but was not found in PATH." >&2
  exit 127
fi

if ! command -v setsid >/dev/null 2>&1; then
  echo "setsid is required but was not found in PATH." >&2
  exit 127
fi

if [[ ! "${timeout_seconds}" =~ ^[0-9]+$ || "${timeout_seconds}" -eq 0 ]]; then
  echo "--timeout must be a positive integer." >&2
  exit 2
fi

if [[ -n "${tango_port}" && ! "${tango_port}" =~ ^[0-9]+$ ]]; then
  echo "--tango-port must be an integer." >&2
  exit 2
fi

accelerator_setup_file="$(realpath "${accelerator_setup_file}")"
lattice_file="$(realpath "${lattice_file}")"

if [[ ! -f "${accelerator_setup_file}" ]]; then
  echo "Accelerator setup file not found: ${accelerator_setup_file}" >&2
  exit 2
fi

if [[ ! -f "${lattice_file}" ]]; then
  echo "Lattice file not found: ${lattice_file}" >&2
  exit 2
fi

if [[ -n "${sif_file}" ]]; then
  sif_file="$(realpath "${sif_file}")"
  if [[ ! -f "${sif_file}" ]]; then
    echo "SIF file not found: ${sif_file}" >&2
    exit 2
  fi
  image_ref="${sif_file}"
else
  image_ref="${image_uri}"
fi

if [[ -z "${log_file}" ]]; then
  log_file="$(mktemp -t dt4acc-twin.XXXXXX.log)"
else
  log_file="$(realpath -m "${log_file}")"
  mkdir -p "$(dirname "${log_file}")"
  : >"${log_file}"
fi

if [[ -n "${pid_file}" ]]; then
  pid_file="$(realpath -m "${pid_file}")"
  mkdir -p "$(dirname "${pid_file}")"
fi

setup_dir="$(dirname "${accelerator_setup_file}")"
setup_base="$(basename "${accelerator_setup_file}")"
lattice_dir="$(dirname "${lattice_file}")"
lattice_base="$(basename "${lattice_file}")"

bind_args=()
if [[ "${setup_dir}" == "${lattice_dir}" ]]; then
  bind_args+=(--bind "${setup_dir}:/data:ro")
  accelerator_setup_container="/data/${setup_base}"
  lattice_container="/data/${lattice_base}"
else
  bind_args+=(--bind "${setup_dir}:/accelerator-setup:ro")
  bind_args+=(--bind "${lattice_dir}:/lattice:ro")
  accelerator_setup_container="/accelerator-setup/${setup_base}"
  lattice_container="/lattice/${lattice_base}"
fi

if [[ -n "${tango_port}" ]]; then
  requested_tango_host="${tango_host}:${tango_port}"
else
  requested_tango_host="${tango_host}"
fi

detected_tango_port=""
twin_pid=""

cleanup() {
  if [[ -n "${twin_pid}" ]] && kill -0 "${twin_pid}" 2>/dev/null; then
    kill -- "-${twin_pid}" 2>/dev/null || kill "${twin_pid}" 2>/dev/null || true
    for _ in {1..10}; do
      if ! kill -0 "${twin_pid}" 2>/dev/null; then
        return
      fi
      sleep 1
    done
    kill -KILL -- "-${twin_pid}" 2>/dev/null || kill -KILL "${twin_pid}" 2>/dev/null || true
  fi
}

detect_tango_port() {
  if [[ -n "${tango_port}" ]]; then
    printf '%s\n' "${tango_port}"
    return 0
  fi

  if [[ ! -s "${log_file}" ]]; then
    return 1
  fi

  local detected
  # The twin also logs an Mexec port for internal IPC; only the Tango host line is relevant here.
  detected="$(
    grep -Eai 'TANGO_HOST|tango[-_ ]host' "${log_file}" \
      | sed -nE 's/.*:([0-9]{2,5}).*/\1/p' \
      | tail -n 1 \
      || true
  )"

  if [[ -n "${detected}" ]]; then
    printf '%s\n' "${detected}"
    return 0
  fi

  return 1
}

echo "Starting dt4acc twin"
echo "  mode:               ${mode}"
echo "  accelerator setup: ${accelerator_setup_file}"
echo "  lattice file:       ${lattice_file}"
if [[ "${mode}" == "tango" ]]; then
  echo "  tango host:         ${tango_host}"
  echo "  tango port:         ${tango_port:-auto}"
  echo "  requested TANGO_HOST: ${requested_tango_host}"
else
  echo "  PV prefix:          ${prefix:-twin default}"
fi
echo "  image:              ${image_ref}"
echo "  log file:           ${log_file}"
if [[ -n "${pid_file}" ]]; then
  echo "  pid file:           ${pid_file}"
fi

trap cleanup INT TERM EXIT

if [[ "${mode}" == "tango" ]]; then
  setsid env TANGO_HOST="${requested_tango_host}" apptainer run \
    "${bind_args[@]}" \
    "${image_ref}" \
    tango-db-embedded \
    --force-kill-db \
    --tango-host "${requested_tango_host}" \
    --accelerator-setup-file "${accelerator_setup_container}" \
    --lattice-file "${lattice_container}" \
    >"${log_file}" 2>&1 &
else
  epics_args=(
    --accelerator-setup-file "${accelerator_setup_container}"
    --lattice-file "${lattice_container}"
  )
  if [[ -n "${prefix}" ]]; then
    epics_args+=(--prefix "${prefix}")
  fi
  setsid apptainer run \
    "${bind_args[@]}" \
    "${image_ref}" \
    epics-embedded \
    "${epics_args[@]}" \
    >"${log_file}" 2>&1 &
fi

twin_pid="$!"
if [[ -n "${pid_file}" ]]; then
  echo "${twin_pid}" >"${pid_file}"
fi
start_epoch="$(date +%s)"

while true; do
  if ! kill -0 "${twin_pid}" 2>/dev/null; then
    echo "dt4acc twin exited before becoming ready. Last log lines:" >&2
    tail -n 200 "${log_file}" >&2 || true
    exit 1
  fi

  if [[ "${mode}" == "tango" && -z "${detected_tango_port}" ]]; then
    if detected_tango_port="$(detect_tango_port)"; then
      echo "Detected Tango database port: ${detected_tango_port}"
      echo "Effective TANGO_HOST: ${tango_host}:${detected_tango_port}"
    else
      detected_tango_port=""
    fi
  fi

  if grep -q "${ready_pattern}" "${log_file}"; then
    if [[ "${mode}" == "tango" && -z "${detected_tango_port}" ]]; then
      if detected_tango_port="$(detect_tango_port)"; then
        echo "Detected Tango database port: ${detected_tango_port}"
        echo "Effective TANGO_HOST: ${tango_host}:${detected_tango_port}"
      else
        echo "Warning: ready heartbeat found, but Tango database port was not detected in logs." >&2
      fi
    fi
    echo "Ready to use"
    if [[ "${detach}" == "1" ]]; then
      trap - EXIT
      disown "${twin_pid}" 2>/dev/null || true
      exit 0
    fi
    break
  fi

  now_epoch="$(date +%s)"
  if (( now_epoch - start_epoch >= timeout_seconds )); then
    echo "Timed out after ${timeout_seconds}s waiting for dt4acc twin readiness. Last log lines:" >&2
    tail -n 200 "${log_file}" >&2 || true
    exit 1
  fi

  sleep 2
done

wait "${twin_pid}"
