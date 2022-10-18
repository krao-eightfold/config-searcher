from config import config
from flatten_dict import flatten
from secrets import token_hex
import sys

from sonic import IngestClient, ControlClient
import glog as log
import json

"""
TODO
https://docs.rs/sonic-channel/latest/sonic_channel/struct.SearchChannel.html
https://github.com/valeriansaliou/sonic
https://github.com/ianlini/flatten-dict

- get all partitions for all needed configs.
- walk the dict config objects and populate feilds: name, partition, path, value, updated_at, url
"""
SONIC_PASSWORD = json.load(open('secrets.json', 'r'))['sonic']['pwd']
COLLECTION = "8f_cfg"
BUCKET = "flat_dicts"

ingestcl = IngestClient("localhost", 1491, SONIC_PASSWORD)
if not ingestcl.ping():
    log.info("Ingest channel inactive.")
    sys.exit(1)

controlcl = ControlClient("localhost", 1491, SONIC_PASSWORD)
if not controlcl.ping():
    log.info("Control channel inactive.")
    sys.exit(1)

# search server exhausts disk space otherwise.
SCHEMAS_ONLY = 1

def main():

    log.info("Flushing bucket %s in collection %s", BUCKET, COLLECTION)
    ingestcl.flush_bucket(COLLECTION, BUCKET)

    configs_names = [v.get('namespace') for v in config.get_all_active_configs_from_db()]
    log.info("Ingesting %d configs", len(configs_names))
    for name in configs_names:
        cfg_partitions = config.get_all_partitions_for_config(name)
        log.info("Ingesting %d partitions for %s", len(cfg_partitions), name)

        for partition in cfg_partitions:
            namespace = partition['namespace']
            if SCHEMAS_ONLY and 'schema' not in namespace:
                continue

            cfg = config.get(namespace)
            try:
                flat = flatten(cfg, reducer='dot')
            except:
                log.exception("Unable to flatten config %s", namespace)
                continue

            for k, _ in flat.items():
                object_id = f'{namespace}.{token_hex(16)}'
                _object = f'{namespace}.{k}'.replace('.', ' ')
                try:
                    ingestcl.push(COLLECTION, BUCKET, object_id, _object)
                except:
                    log.exception('unable to push %s, v: %s', object_id, _object)
                    import pdb; pdb.set_trace()

    log.info("Indexing status: %s", controlcl.trigger("consolidate"))
    log.info('Object count after indexing: ', ingestcl.count(COLLECTION, BUCKET))


if __name__ == "__main__":
    main()
    # log.info('Object count after indexing: %s', ingestcl.object_count(COLLECTION, BUCKET))
