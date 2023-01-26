import os, socket, sys, ssl, OpenSSL
import subprocess, paramiko
from scp import SCPClient
from contextlib import closing
from modules import logs, dockerutils, colours
from modules import time, sources, registry
from datetime import datetime
from paramiko.ssh_exception import AuthenticationException
from paramiko.ssh_exception import SSHException, BadHostKeyException

# Synchronize private keys of signed images for Notary
class PrivKeySync:
    keysync_server_address = os.environ.get('KEYSYNC_SERVER_IP')
    keysync_server_user = os.environ.get('KEYSYNC_SERVER_USER')
    target_keys = os.environ.get('NOTARY_REMOTE_KEYS_PATH')
    local_keys = os.environ.get('NOTARY_LOCAL_KEYS_PATH')

    if keysync_server_address is None:
       raise Exception(colours.red("notary KEYSYNC_SERVER_IP does not defined!"))
    elif keysync_server_user is None:
       raise Exception(colours.red("notary KEYSYNC_SERVER_USER does not defined!"))
    elif target_keys is None:
       raise Exception(colours.red("notary NOTARY_REMOTE_KEYS_PATH does not defined!"))
    elif local_keys is None:
       raise Exception(colours.red("notary NOTARY_LOCAL_KEYS_PATH does not defined!"))

    # Creates notary private key folders to store signature data in local image
    def set_signature_dir():
        try:
            keys_folder = "/root/.docker/trust/private"
            if not os.path.exists(keys_folder):
                os.makedirs(keys_folder)
                for root, _, dirs in os.walk("/root/.docker"):
                    os.chmod(root, 0o700)
        except OSError:
            raise

    try: # SSH trust must be done to sync all signature keys of notary
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(username=keysync_server_user, hostname=keysync_server_address)
    except (AuthenticationException, SSHException, BadHostKeyException):
        raise

    try:
        # Checks and sets the correct permission owner for signature folders in target server
        # Timeout: takes non-negative float value to be set seconds
        stdin_, stdout_, stderr_ = ssh.exec_command(f"sudo chown -R {keysync_server_user}. {target_keys}", get_pty=True, timeout=10.0)
        for remote_ssh_out in iter(stdout_.readline, ""):
            print(remote_ssh_out, end="")
    except Exception as err:
        print(colours.red(f"Check sudo settings on {keysync_server_address} for {keysync_server_user} user {err}"))
        raise

    scp_strcmd = lambda: SCPClient(PrivKeySync.ssh.get_transport())
    '''
        This is a simple lambda function that returns a string
        More readable functions is here

        def scp_strcmd():
            return SCPClient(..)
    '''

    # Sync private keys from target place
    def dest_sync():
        with PrivKeySync.scp_strcmd() as scp:
            scp.get(PrivKeySync.target_keys + "/", local_path="/root/", preserve_times=True, recursive=True)

    # Sync private keys from local place
    def src_sync():
        with PrivKeySync.scp_strcmd() as scp:
            scp.put(PrivKeySync.local_keys + "/trust/", remote_path=PrivKeySync.target_keys + '/trust/',  preserve_times=True, recursive=True)

    # Remove unnecessary old config of docker client
    def remove_config(file=f"{local_keys}/config.json"):
        if os.path.exists(file):
            remove_config_out=subprocess.run([f"rm -f {file}"], shell=True)
            if remove_config_out.returncode > 0:
                print(colours.red(f"local docker config file could not removed! {remove_config_out}"))

class Notary:
    server_port = 4443
    server_ip = os.environ.get('NOTARY_SERVER_IP')
    signer_auth_pass = os.environ.get('DOCKER_CONTENT_TRUST_ROOT_PASSPHRASE')
    docker_trust_server = os.environ.get('DOCKER_CONTENT_TRUST_SERVER')
    server_uri = docker_trust_server.replace('https://', '').replace(':' + str(server_port), '')

    content_trust = "DOCKER_CONTENT_TRUST"
    os.environ[content_trust] = "1" # env var must be set string

    # Check signer/notary env is set
    def signer_env_check():
        signer_repo_pass = os.environ.get('DOCKER_CONTENT_TRUST_REPOSITORY_PASSPHRASE')

        if (Notary.content_trust in os.environ and Notary.docker_trust_server):
           print(colours.green(f"Image signer server: {Notary.docker_trust_server}\nDocker content trust: Enable"))
        else:
            raise ValueError(f"{Notary.content_trust} or {Notary.docker_trust_server} does not defined!")

        if (Notary.signer_auth_pass is None
           or signer_repo_pass is None):
            raise Exception(colours.red("Image signer credential(s) is not defined!"))
        else:
            print(colours.green("Image signer and repo password are defined."))

    # Check signer/notary server is accessible
    def connection_check():
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                sock.settimeout(3)
                if sock.connect_ex((Notary.server_uri, Notary.server_port)) == 0:
                    print(colours.green(f"Signer server({Notary.server_uri}) is accessible."))
                else:
                    raise RuntimeError(f"Cannot access to {Notary.server_uri}:{Notary.server_port} IP: {Notary.server_ip}")
        except socket.error as s:
            print("exception socket.error : %s" % s)

    # Check signer ca cert is placed in correct area.
    def cert_file_check(path, file="notary-root-ca-test.crt"):
        if os.path.exists(path):
            if os.path.isfile(f"{path}/{file}"):
                return print(colours.green(f"CA cert is in correct place: {path}/{file}"))
            else:
                raise Exception(colours.red(f"{file} Signer CA cert is not installed in {path}"))
        else:
            raise Exception(colours.red(f"Cannot access to the signer CA cert folder: {path}"))

    def cert_validity_check():
        cert = ssl.get_server_certificate((Notary.server_uri, Notary.server_port))
        x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)

        if x509.get_subject().commonName == Notary.server_uri:
            get_expire_date = datetime.strptime(x509.get_notAfter().decode('ascii'), '%Y%m%d%H%M%SZ')
            expire_in = get_expire_date - datetime.now()

            if expire_in.days >= 90: # Check cert if validity equal or less than 3 months.
                print(colours.green(f"OK - Notary certificate is valid for: {expire_in}"))
            else:
                print(colours.red(f"WARNING - Notary cert will be expired in: {expire_in}"))
            if x509.has_expired(): # Returns "false" if cert is not expired yet.
                raise Exception(colours.red("Critical - Notary cert is expired. Process is exited!"))

class Docker:
    # Check image IF it is already signed before
    def check_existing_signed(image, notary_bin, notary_server, registry_host):
        image_name = image.split(":")[0]
        tag = image.split(":")[-1] + "-signed"

        notary_cmd = f"{notary_bin} -s {notary_server} -d ~/.docker/trust lookup {registry_host}"
        check_signed_image = subprocess.run([f"{notary_cmd}/signed/{str(image_name)} {tag}"],
            stdout=subprocess.PIPE, shell=True, encoding='utf-8')
        if check_signed_image.returncode is not None:
            return check_signed_image
        else:
            print(colours.red(f"{check_signed_image.stdout}"))

    # Enables image content trust, and then sign & push the image into registry
    def push_signed_image(signed):
        try:
            if Notary.content_trust in os.environ:
                push_image = subprocess.Popen([f"docker push {signed}"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True, encoding='utf-8')
                print(push_image.communicate(input='{0}\n'.format(Notary.signer_auth_pass))[0])

                if push_image.returncode == 0:
                    print(colours.green(f"{signed} is successfully signed & pushed to registry."))
                    return push_image.stdout
                else:
                    raise Exception(colours.red(f"{signed} Image cannot signed & pushed into the registry!"))
        except (TypeError, KeyError):
            raise

def push_images():
    dockerutils.command.registry_login()
    Notary.signer_env_check()
    list_image = sources.image.load_sourcelist()
    notary_host_address = dockerutils.command.notary_server()
    ca_cert_path = "/usr/local/share/ca-certificates"
    Notary.cert_file_check(ca_cert_path)
    Notary.connection_check()
    Notary.cert_validity_check()

    logs.event.logger.info("[1/2] Notary: synchronizing old signed private keys.")
    PrivKeySync.set_signature_dir()
    PrivKeySync.dest_sync()

    sign_image = dockerutils.command.get_signed_images()
    image_count = len(sign_image)

    for baseimage, signed in zip(list_image, sign_image):
        check_signed = Docker.check_existing_signed(baseimage, dockerutils.notary_path, notary_host_address, registry.host)
        if check_signed.stdout != '':
            if check_signed.returncode == 1:
                Docker.push_signed_image(signed)
            elif (check_signed.returncode == 0) and ("-signed" in check_signed.stdout):
                print(colours.blue(f"{baseimage} image is already signed. Skipping to sign and push once again!"))
            time.WaitNextProcess.set_sleep_time(3, image_count)
        else:
            print(check_signed)

    logs.event.logger.info("[2/2] Notary: synchronizing new signed private keys.")
    PrivKeySync.remove_config()
    PrivKeySync.src_sync()

if __name__ == "__main__":
  push_images()
