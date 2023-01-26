import os, subprocess
from modules import colours
from modules import dockerutils

class Notary:
    # Checks if notary is installed correct place
    def check_client(notary_bin):
        if not os.path.isfile(notary_bin):
            raise Exception(colours.red(f"Notary binary: '{notary_bin}' does not installed!"))

    # Returns details of signed image
    def check_signer(signed_image, notary_bin, notary_server):

        image_name = signed_image.split(":8083/signed/")[1].split(":")[0]  # e.g. alpine
        image_tag = signed_image.split(":")[-1]  # e.g. 3.13.14-signed
        image_address = signed_image.split("/")[0] # e.g. am2vm2258.test.igdcs.com:8083
        try:
            notary_cmd = f"{notary_bin} -s {notary_server} -d ~/.docker/trust lookup {image_address}/signed/"
            check_image = subprocess.run([
            f"{notary_cmd}{image_name} {image_tag}"],
            stdout=subprocess.PIPE, shell=True, encoding='utf-8')
        except subprocess.CalledProcessError:
            raise

        if check_image.stdout is not None:
            if check_image.returncode == 0:
                print(colours.green(f"Sign details of image: {image_name} {check_image.stdout}"))
                return f"{image_address}/signed/{image_name}:{image_tag}"
            else:
                print(colours.red(f"Cannot access signature: {image_name}:{image_tag} {check_image.stdout}"))

    # Lists full path of scanned and signed image
    def pull_info(image_name):
        for signed_img in image_name:
            print(signed_img)

def notary_main():
    Notary.check_client(dockerutils.notary_path)
    list_image = dockerutils.command.get_signed_images()
    notary_address = dockerutils.command.notary_server()

    image_list = []
    if list_image is not None:
        for image_name in list_image:
            signer_result = Notary.check_signer(image_name, dockerutils.notary_path, notary_address)
            if signer_result is not None:
               image_list.append(signer_result)

    print(colours.green("Pull image:"))
    Notary.pull_info(image_list)

if __name__ == "__main__":
  notary_main()
