import sys
import AbstractionLayers
import DatabaseDriver


def main():
    if len(sys.argv) > 1:
        cmd = ["fatrace", "-p", sys.argv[1]]
    else:
        cmd = ["fatrace"]

    try:
        AbstractionLayers.FAstream(cmd, printflag=True)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        DatabaseDriver.close()
        DatabaseDriver.graph_cache_results()


if __name__ == "__main__":
    main()
