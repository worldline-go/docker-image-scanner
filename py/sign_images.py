from modules import logs, colours
from modules import dockerutils, registry
from docker.errors import APIError

class SignImage:
    def tag_image(quarantine_image):
        '''
        Tagging image from quarantine to prepare it
        for sign and push process in next stage.
        '''
        if len(quarantine_image) > 0:
            clear_quarantine = quarantine_image.split('quarantine/')[-1]
            global new_sign_name
            try:
                new_sign_name = f"{registry.host}/signed/{clear_quarantine}-signed"
                dockerutils.api.tag(quarantine_image, new_sign_name)
            except APIError:
                raise

logs.event.logger.info("[1/1] Tagging image from quarantine:")

def tag_images():
    images = dockerutils.command.get_quarantined_images()
    for image in images:
        SignImage.tag_image(image)
        print(colours.blue(f"{image} is tagged > {new_sign_name}"))

    print(colours.green(f"{str(len(images))} image is successfully tagged."))

if __name__ == "__main__":
  tag_images()
