import os
from modules import logs

logs.event.logger.debug("Loading docker images:")

class image(object):
    def load_sourcelist(filepath="./sources"):
        sources = []
        origin_file = filepath.strip("./")
        if os.path.getsize(origin_file) > 0: # Check if file empty
            with open(filepath) as file:
                uniq_img =  list(dict.fromkeys(file))
                for line in uniq_img:
                    line = line.strip()
                    if (line.strip() != '') and ( not line.startswith('#')): # Skip blank and comment-out lines
                        sources.append(line)
            return sources
        else:
            raise Exception("Image source file is empty!")
