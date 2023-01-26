from modules import dockerutils, logs, colours
from docker.errors import APIError

class clean:
    def unused_data(image_list):
        """
        This function removes scanned containers and images which does not use anymore.
        :param container.id[0:12]: Displays short ID of container instead of long address
        """
        if image_list:
            for image in image_list:
                try:
                    container_list = dockerutils.client.containers.list(filters={"status":"running", "ancestor":image})
                    if container_list:
                        for get_container in container_list:
                            container = dockerutils.client.containers.get(get_container.id)
                            container.remove(force=True)
                            print(colours.green("Container is removed: "), f"{container.id[0:12]}")
                except APIError:
                    raise
                try:
                    dockerutils.client.images.remove(image, force=True)
                    print(colours.green("Image is removed: "), f"{image}")
                except APIError:
                    pass

quarantine_image = dockerutils.command.get_quarantined_images()
signed_image = dockerutils.command.get_signed_images()
all_images = quarantine_image + signed_image

logs.event.logger.info("Starting cleaning progres:")
clean.unused_data(all_images)
