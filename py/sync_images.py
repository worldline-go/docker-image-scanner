from docker.errors import APIError, ImageNotFound
from modules import logs, sources, dockerutils

class SyncImage():
    def remove_image(image):
        try:
            check_image = dockerutils.client.images.get(image)
            dockerutils.client.images.remove(image, force=True)
        except APIError:
            pass

    # Pull image from public registry and move it in quarantine
    def pull_image(image):
        try:
            dockerutils.client.images.pull(image)
        except APIError:
            raise
        try:
            image_address=dockerutils.client.images.get(image)
            image_address.tag(f"quarantine/{image}", tag=image.split(':')[-1])
        except (ImageNotFound, APIError):
            raise

    # Returns local image to check if it is in quarantine.
    def get_local_images():
        local_images = []
        for local_image_list in dockerutils.client.images.list():
            for add_image in local_image_list.tags:
                local_images.append(add_image)
        return local_images

    def fixed_image_tag(image):
        """
        If latest tag is empty, it is set to :latest
        Note that this feature is already implemented in SDK:
        docker.models.images.ImageCollection.pull
        """
        image_latest_tag = f"quarantine/{image}:latest"
        return image_latest_tag

    # Pull image from target source IF it is not in quarantine
    def get_images_to_pull(sources, local_images):
        pull_list = []
        for image in sources:
          quarantine_path = f"quarantine/{image}"
          quarantine_msg = "Image: %s found in quarantine. Nothing to fetch"
          if quarantine_path in local_images:
              logs.event.logger.info(quarantine_msg % quarantine_path)
          elif SyncImage.fixed_image_tag(image) in local_images:
              logs.event.logger.info(quarantine_msg % quarantine_path + " (:latest tag)")
          else:
              pull_list.append(image)
        return pull_list

def sync_images():
    pull_list = SyncImage.get_images_to_pull(sources.image.load_sourcelist(), SyncImage.get_local_images())

    if len(pull_list) == 0:
      logs.event.logger.info("Nothing to do")
    else:
        logs.event.logger.info("Found %d new images to move in quarantine" % len(pull_list))
        for image in pull_list:
            col_char = ":"
            if (col_char not in image) and (SyncImage.fixed_image_tag(image)
            not in SyncImage.get_local_images()):
                image = f"{image}:latest"
            else:
                image = image
            logs.event.logger.info("##### [%s] ######" % image)
            logs.event.logger.info("[1/4] Remove local copy of image: %s" % image)
            SyncImage.remove_image(image)
            logs.event.logger.info("[2/4] Pull image: %s" % image)
            SyncImage.pull_image(image)
            logs.event.logger.info("[3/4] Quarantine image: %s to [quarantine/%s]" % (image, image))
            logs.event.logger.info("[4/4] Remove local copy of image: %s" % image)
            SyncImage.remove_image(image)
if __name__ == "__main__":
    sync_images()
