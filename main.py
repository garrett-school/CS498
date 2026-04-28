import sys
import AbstractionLayers
import DatabaseDriver


def main():
    if len(sys.argv) > 1:
        cmd = ["fatrace", "-p", sys.argv[1]]
    else:
        cmd = ["fatrace"]

    db = DatabaseDriver.SnapshotDB()
    receiver = DatabaseDriver.SnapshotReceiver(db)

    AbstractionLayers.BatchSend = DatabaseDriver.patched_batch_send_factory(
        receiver, AbstractionLayers.BatchSend
    )
    AbstractionLayers.TryCache = DatabaseDriver.patched_trycache_factory(
        receiver, AbstractionLayers.TryCache
    )

    try:
        AbstractionLayers.FAstream(cmd, printflag=True)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        db.close()
        DatabaseDriver.graph_cache_results()


if __name__ == "__main__":
    main()
