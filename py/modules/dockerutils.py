import subprocess, os, docker
from modules import colours, dockerutils
from modules import registry, sources
from docker.errors import APIError, ImageNotFound, NotFound

# Client of docker sdk for daemon socket
client = docker.from_env()
# Low-level API of docker sdk
api = docker.APIClient()
# Docker Notary binary path
notary_path = "/usr/bin/notary"

class command:
     # Keep unique image list while preserving order
     image_list = list(dict.fromkeys(sources.image.load_sourcelist()))

     def start_container(image):
         try: # spin-up container with default or a custom entrypoint
             entrypoint = os.environ.get('ENTRYPOINT')
             if (entrypoint is not None and entrypoint !=""):
                 argument = entrypoint
                 print(colours.red(f"Custom entrypoint: {argument}"))
             else:
                 argument = "/bin/sh"
             container = client.containers.run(
             image, entrypoint=argument, tty=True, detach=True)
         except (ImageNotFound, APIError): # spin-up container on these exceptions without an entrypoint
             container = client.containers.run(image, tty=True, detach=True)
         return container.id

     # Check health status of started container.
     def check_container_health(container_id):
         container_health = subprocess.run(
         [f"docker inspect -f '{{{{.State.Running}}}}' {container_id}"],
            stdout=subprocess.PIPE, shell=True, encoding='utf-8')
         if container_health.returncode == 0:
             if container_health.stdout.strip() == "true":
                 return True
             else:
                 return False

     # Prints container logs if it is failed during startup.
     def pre_check_result(image, container_id):
         container_status = command.check_container_health(container_id)
         if container_status is False:
             try:
                 container = client.containers.get(container_id)
                 container.logs
             except APIError:
                 raise Exception("scanning is stopped!")

     def kill_container(cid):
         try:
             container = client.containers.get(cid)
         except NotFound:
             raise
         try:
            container.kill()
            raise Exception("container is killed!", container.id)
         except APIError:
             raise

     # Returns a list of containers that are tagged "quarantine/*"
     def get_quarantined_images():
         quarantine = ['quarantine/' + img_name for img_name in command.image_list]
         return quarantine

     def get_signed_images():
         signed = [f"{registry.host}/signed/{img_name}-signed" for img_name in command.image_list]
         return signed

     # Logins to the target docker registry
     def registry_login():
         try:
             subprocess.run([
             f"docker login -u {registry.user} -p {repr(str(registry.pwd))} {registry.host}"],
             stdout=subprocess.PIPE, shell=True)
         except subprocess.CalledProcessError:
             raise

     # Check signer server env is set
     def notary_server():
         notary_server = os.environ.get('DOCKER_CONTENT_TRUST_SERVER')
         if notary_server is not None:
             return notary_server
         else:
             print(colours.red("DOCKER_CONTENT_TRUST_SERVER env does not defined!"))

     # Copy scanner source(compliance and malware) into target the container
     def copy_files_to_container(container_id, sourcefile, targetdir):
         if os.path.exists(f"{sourcefile}"):
             try:
                 container = dockerutils.client.containers.get(container_id)
                 cmd_result = container.exec_run(f"mkdir -p {targetdir}", privileged=True)

                 if cmd_result:
                     try:
                         with open(f"{sourcefile}", 'rb') as pkg:
                            pkg_move_result = container.put_archive(path=f"{targetdir}", data=pkg)
                            if pkg_move_result is True:
                                print(colours.blue(f"{sourcefile}, is successfully moved into the {container_id}"))
                     except (APIError, OSError):
                         dockerutils.command.kill_container(container_id)
                         raise
                 else:
                     raise Exception(cmd_result)
             except (APIError, NotFound):
                 raise
         else:
             dockerutils.command.kill_container(container_id)
             raise Exception(f"{sourcefile} does not exist!")
