"""Client d'exécution Python à distance, lancé avec le Python Windows d'Unreal (pas celui de WSL) :
le multicast de découverte de l'éditeur ne traverse pas la frontière WSL / Windows.

    <UE>/Engine/Binaries/ThirdParty/Python3/Win64/python.exe remote_client.py <plugin_python_dir> <script.py> [timeout]

Sortie : la sortie du script, puis une dernière ligne « BARQUE_REMOTE_STATUS ok|error|absent ».
Code retour : 0 succès, 1 échec du script, 2 aucun éditeur joignable.
"""
import sys
import time

sys.path.insert(0, sys.argv[1])
import remote_execution as rx  # noqa: E402

script, timeout = sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
config = rx.RemoteExecutionConfig()
config.multicast_bind_address = "127.0.0.1"
remote = rx.RemoteExecution(config)
remote.start()
try:
    deadline = time.time() + timeout
    while not remote.remote_nodes and time.time() < deadline:
        time.sleep(0.2)
    nodes = remote.remote_nodes
    if not nodes:
        print("BARQUE_REMOTE_STATUS absent")
        sys.exit(2)
    remote.open_command_connection(nodes[0]["node_id"])
    result = remote.run_command(script, unattended=True, exec_mode=rx.MODE_EXEC_FILE)
    for entry in result.get("output", []):
        print(entry.get("output", "").rstrip())
    if result.get("result") not in (None, "None", ""):
        print(result["result"])
    ok = result.get("success", False)
    print(f"BARQUE_REMOTE_STATUS {'ok' if ok else 'error'}")
    sys.exit(0 if ok else 1)
finally:
    remote.stop()
