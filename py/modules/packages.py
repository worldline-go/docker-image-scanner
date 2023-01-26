import os, subprocess
from modules import colours
from modules import dockerutils
from docker.errors import APIError, NotFound

docker_cmd = "docker exec --privileged -u 0 -i "

available_os = {
    'centos': { # Centos Linux
        'package_name': 'util-linux wget ncurses e2fsprogs diffutils file lsof passwd bind-utils net-tools',
        'command': 'yum install -y',
        'package_manager': 'RPM',
    },
    'rhel': { # Redhat Linux
        'package_name': 'util-linux e2fsprogs diffutils file lsof passwd bind-utils net-tools',
        'command': 'yum install -y',
        'package_manager': 'RPM',
    },
    'debian': { # Debian Linux
        'package_name': 'util-linux tree mtree-netbsd net-tools procps curl host lsof dnsutils debsums binutils file kmod',
        'command': 'apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y',
        'package_manager': 'DPKG',
    },
    'ubuntu': { # Ubuntu Linux
        'package_name': 'util-linux tree net-tools procps curl host lsof dnsutils debsums binutils file kmod',
        'command': 'apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y',
        'package_manager': 'DPKG',
    },
    'alpine': { # Alpine Linux
        'package_name': 'curl bind-tools file e2fsprogs-extra coreutils util-linux tree',
        'command': 'apk update && apk add',
        'package_manager': 'NONE',
    },
    'amzn': { # Amazon Linux
        'package_name': 'curl bind-tools file e2fsprogs-extra coreutils passwd bind-utils net-tools procps',
        'command': 'yum install -y',
        'package_manager': 'RPM',
    },
    'ol': { # Oracle Linux
        'package_name': 'bind-utils file net-tools lsof hostname tree findutils procps passwd',
        'command': 'dnf install -y',
        'package_manager': 'RPM',
    },
    'sles': { # Suse Linux
        'package_name': 'curl awk bind-utils file net-tools lsof iproute2 e2fsprogs',
        'command': 'zypper install -y',
        'package_manager': 'NONE',
    },
    'fedora': { # Fedora Linux
        'package_name': 'procps util-linux wget ncurses e2fsprogs diffutils file lsof passwd bind-utils net-tools',
        'command': 'dnf install -y',
        'package_manager': 'RPM',
    },
    'rocky': { # Rocky Linux
        'package_name': 'findutils procps util-linux wget ncurses e2fsprogs diffutils file lsof passwd bind-utils net-tools',
        'command': 'dnf install -y',
        'package_manager': 'RPM',
    },
    'photon': { # Photon VMware/Linux
        'package_name': 'awk ncurses coreutils util-linux wget ncurses e2fsprogs diffutils file lsof net-tools',
        'command': 'tdnf install -y',
        'package_manager': 'NONE',
    },
}

class MissingPackage:
    def add_package(container_id, change_pkg_manager):

        os_file_path = "/etc/os-release"
        find_os_cmd1 = f"source {os_file_path}; echo $ID"
        find_os_cmd2 = f"grep ID {os_file_path}|tr -d 'ID='|grep -v '_'|sed -n 1p"

        check_os_type = subprocess.run([f"{docker_cmd}{container_id} \
                /bin/sh -c '{find_os_cmd1}'"], stdout=subprocess.PIPE, shell=True, encoding='utf-8')

        check_os_fallback = subprocess.run([f"{docker_cmd}{container_id} \
                /bin/sh -c '{find_os_cmd2}'"], stdout=subprocess.PIPE, shell=True, encoding='utf-8')

        if (check_os_type.stdout != "\n") and (check_os_type.returncode == 0):
            current_os = check_os_type.stdout
            print(colours.green("Image type is detected: "), current_os)
        else:
            current_os = check_os_fallback.stdout
            print(colours.blue("Falling back to find image type with a different method: "), current_os)
            if (not current_os) or (check_os_fallback.returncode != 0):
                print(colours.red("Image type cannot be detected. Skipping..."))
                pass

        for os_name, os_package in available_os.items():
            if os_name in current_os:
                run_result = subprocess.run(
                    [f"{docker_cmd}{container_id} \
                    /bin/sh -c '{os_package['command']} {os_package['package_name']}'"],
                        shell=True)
                if (run_result.returncode != 0):
                    print(run_result.stdout)

                # Auto-fix for find command due to the missing yum pkg on some centos/rhel type images.
                if (run_result.returncode != 0) and ("centos" in current_os or "rhel" in current_os):
                    missing_pkg = "findutils"
                    if os.path.exists(f"/opt/{missing_pkg}.tar.gz"):
                        try:
                            container = dockerutils.client.containers.get(container_id)
                            with open(f"/opt/{missing_pkg}.tar.gz", 'rb') as pkg:
                                container.put_archive(path="/tmp", data=pkg)
                        except (APIError, NotFound, OSError):
                            pass
                        try:
                            exec_out = container.exec_run(
                                f"rpm -i /tmp/opt/{missing_pkg}.rpm",
                                privileged=True,
                                user="root")
                            if exec_out and exec_out.exit_code == 0:
                                print(colours.blue("fallback: missing find command is installed!"), exec_out)
                            else:
                                print(exec_out)
                        except APIError:
                            pass
                    else:
                        print(colours.red(f"{missing_pkg}.rpm couldn't find in pre-build image!"))
                else:
                    pass

                # Auto-fix for Oracle Linux Slim images to handle its missing package manager.
                if (run_result.returncode != 0) and ("ol" in current_os):
                    subprocess.run(
                    [f"{docker_cmd}{container_id} \
                    /bin/sh -c 'microdnf install -y {os_package['package_name']}'"],
                        shell=True)

                if change_pkg_manager is True: # Set package manager in malware scanning part.
                    rkhunter_config = "/tmp/rkhunter/etc/rkhunter.conf"
                    change_pkg_manager = subprocess.run(
                        [f"{docker_cmd}{container_id} \
                        /bin/sh -c 'sed -i 's/#PKGMGR=NONE/PKGMGR={os_package['package_manager']}/g' \
                        {rkhunter_config}'"], shell=True)
