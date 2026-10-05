import argparse

from .chroma_store import ChromaStore
from .loaders import LOADERS
from .sources.factory import SourceFactory


def build(only: str | None, fresh: bool, skip_download: bool) -> None:
    store = None

    for source in SourceFactory.load(only):
        print(f"\n== {source.config.id}: {source.config.title}")
        try:
            source.download(fresh=fresh, skip_download=skip_download)

            if source.config.store == "postgres":
                if source.config.id not in LOADERS:
                    raise ValueError(f"No Postgres loader for '{source.config.id}'")
                written = LOADERS[source.config.id](source)
                print(f"   rows={written}")
                continue

            pages = source.extract()
            chunks = source.chunk(pages)

            if store is None:
                store = ChromaStore()
            written = store.upsert(chunks)

            print(f"   pages={len(pages)} chunks={len(chunks)} stored={written}")
        except NotImplementedError as e:
            print(f"   TODO: implement {e} to continue")
            return
        except Exception as e:
            print(f"   FAILED: {type(e).__name__}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the knowledge base into Chroma and Postgres.")
    parser.add_argument("--only", help="process a single source id")
    parser.add_argument("--query", help="search the knowledge base instead of building it")
    download_mode = parser.add_mutually_exclusive_group()
    download_mode.add_argument("--fresh", action="store_true", help="re-download even if the file exists")
    download_mode.add_argument("--skip-download", action="store_true", help="use files already in raw/ only")
    args = parser.parse_args()

    if args.query:
        for hit in ChromaStore().query(args.query):
            print(hit)
    else:
        build(args.only, args.fresh, args.skip_download)


if __name__ == "__main__":
    main()
