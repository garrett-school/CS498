import subprocess
from time import ctime
import os
import IntellegentInterface
import DatabaseDriver

FullIOList = []
FullSuggestionList = []

# def process_continuous_output(cmd):
#     # bufsize=1 enables line buffering; shell=False is safer if cmd is a list
#     p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1)
#
#     try:
#         for line in iter(p.stdout.readline, b""):
#             # Process each line as it arrives
#             deliniator = " "
#             line = line.decode().strip()
#             line = deliniator + line.partition(deliniator)[2]
#             print(line)
#     finally:
#         p.stdout.close()
#         p.stderr.close()
#         p.wait()


def FAstream(cmd, printflag=False):
    # bufsize=1 enables line buffering; shell=False is safer if cmd is a list
    deliniator = " "
    batchsize = 25  # may want to increase for the PoC to reduce API tokens!

    # cwd = os.getcwd().rpartition("/")[2]

    # try:
    #     dbstat = os.stat(DBname)
    # except:
    #     dbstat = os.stat("/")
    #

    currentPID = os.getpid()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1)
    queue = []
    try:
        try:
            for line in iter(p.stdout.readline, b""):
                # Process each line as it arrives
                line = line.decode().strip()

                strippedline = "/" + line.partition("/")[2]
                ioPID = int(
                    line.partition(":")[0].rpartition("(")[2].rpartition(")")[0]
                )
                # ioPID = int(line.partition("(")[2].partition(")")[0])
                # extrastrippedline = line.rpartition("/")[2]
                # linestat = os.stat(strippedline)
                # (
                #     (extrastrippedline == DBname)
                #     or (extrastrippedline == (DBname + "-journal"))
                #     or (extrastrippedline == cwd)
                # )
                # not os.path.samestat(dbstat, linestat)
                cond = currentPID != ioPID
                if cond:
                    line = ctime() + deliniator + line.partition(deliniator)[2]
                    queue.append(line + "\n")
                    if len(queue) >= batchsize:
                        paths_to_cache = BatchSend(queue)
                        cache_result = TryCache(
                            paths_to_cache
                        )  # cahnged only this line - john
                        queue = []
                    if printflag:
                        print(line)
        except:
            print("ERROR!!! <><><><><><><><><><><><><><><><><><><><><><>")
            print(line)
            print(currentPID)
            print(ioPID)
            raise

    finally:
        p.stdout.close()
        p.stderr.close()
        p.wait()


def BatchSend(WhatToSendToAI):
    snapshot_id = DatabaseDriver.save_snapshot(WhatToSendToAI)
    suggestions = IntellegentInterface.get_file_suggestions(WhatToSendToAI)
    for path in suggestions:
        result = TryCache(path)
        DatabaseDriver.save_cache_attempt(path, result, snapshot_id)
    return suggestions


def TryCache(path):
    try:
        with open(path, "rb") as file:
            while file.read(4096):
                pass
        return 1
    except:
        return -1


# Example usage with a continuous command (replace 'fatrace' with actual args)
if __name__ == "__main__":
    FAstream(["fatrace", "-p", "1234"], 1)
