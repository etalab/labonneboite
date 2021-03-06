import logging
logger = logging.getLogger('main')
formatter = logging.Formatter("%(levelname)s - IMPORTER - %(message)s")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

import sys
import os
from labonneboite.importer import util as import_util


if __name__ == "__main__":
    filename = import_util.detect_runnable_file("etablissements")
    if filename:
        try:
            f = open(os.path.join(os.environ["WORKSPACE"], "properties.jenkins"), "w")
            f.write("LBB_ETABLISSEMENT_INPUT_FILE=%s\n" % filename)
            f.close()
        except KeyError:
            logger.warn("WORKSPACE environment variable does not exist. If I was called outside of Jenkins, this is normal !")

        sys.exit(0)
    else:
        sys.exit(-1)
